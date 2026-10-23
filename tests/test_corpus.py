# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Admission contracts and native observations; dummy bytes stay temporary."""
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("corpus", ROOT / "tools/corpus.py")
corpus = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(corpus)


class CorpusTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="openswx-corpus-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("schemas", "recipes"):
            shutil.copytree(ROOT / name, self.root / name)
        (self.root / "cases").mkdir()
        shutil.copy(ROOT / "plan.json", self.root / "plan.json")
        self.case = self.root / "cases/part-cylinder-001"

    def write_json(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def artifact(self, role, path):
        raw = (self.case / path).read_bytes()
        item = {"role": role, "path": path, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        self.manifest["artifacts"].append(item)
        return item

    def save(self):
        self.write_json(self.case / "case.json", self.manifest)

    def update(self, path, value):
        self.write_json(self.case / path, value)
        item = next(a for a in self.manifest["artifacts"] if a["path"] == path)
        raw = (self.case / path).read_bytes()
        item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        self.save()

    def make_case(self):
        self.case.mkdir()
        recipe = corpus.read_recipe(self.root, "recipes/part-cylinder-001.json", self.case.name)
        self.native = {
            "schema_version": 1, "configuration": "Default", "document_revision": "r1",
            "coordinate_frame": "document", "length_unit": "metre", "unavailable_fields": [],
            "bodies": [{"key": "body", "kind": "solid", "counts": {},
                        "measurements_si": corpus.analytic_measures(recipe)}]}
        self.manifest = {
            "schema_version": 1, "id": self.case.name, "document_kind": "part",
            "configuration": "Default", "document_revision": "r1",
            "recipe": "recipes/part-cylinder-001.json", "tags": ["cylinder"],
            "producer": {"application": "SolidWorks", "year": 2025, "build": "test-only",
                         "worker_version": "test-only", "captured_at": "2026-10-23T12:00:00Z"},
            "provenance": {"origin": "original_synthetic", "author": "unit test",
                           "license": "MIT", "description": "Temporary dummy bytes, not CAD."},
            "tolerances": {"length_absolute_m": 1e-8, "measure_relative": 1e-9,
                           "area_absolute_m2": 1e-14, "volume_absolute_m3": 1e-17,
                           "angle_absolute_rad": 1e-9},
            "expectations": {s: {"outcome": "pass", "reason": "Contract test only."}
                             for s in corpus.STAGES}, "artifacts": []}
        self.exports = []
        for role, path in (("source", "source.sldprt"), ("parasolid_binary", "ref.x_b"),
                           ("parasolid_text", "ref.x_t"), ("step_reference", "ref.step")):
            (self.case / path).write_bytes(b"Temporary contract test; not a CAD file.")
            artifact = self.artifact(role, path)
            if role in corpus.REFERENCE_ROLES:
                self.exports.append({"artifact_path": path, "bytes": artifact["bytes"],
                    "sha256": artifact["sha256"], "format": role, "configuration": "Default",
                    "document_revision": "r1", "selection_scope": "whole_document",
                    "length_unit": "metre", "source_to_metre_scale": 1.0,
                    "format_version": "ISO-10303-21" if role == "step_reference" else "test",
                    "verification": "verified", "warnings": []})
        self.exports[-1]["application_protocol"] = "AP214"
        for role, path, data in (("native", "native.json", self.native),
                ("capabilities", "capabilities.json", {"test_only": True}),
                ("export_receipts", "receipts.json", {"schema_version": 1, "exports": self.exports})):
            self.write_json(self.case / path, data)
            self.artifact(role, path)
        self.save()

    def test_preparation_is_not_coverage(self):
        report = corpus.audit(self.root)
        self.assertEqual((report["planned_cases"], report["captured_cases"]), (50, 0))
        self.assertFalse(report["library_tests_executed"])
        with self.assertRaisesRegex(corpus.CorpusError, "no captured cases"):
            corpus.audit(self.root, True)

    def test_valid_contract_is_not_library_pass(self):
        self.make_case()
        report = corpus.audit(self.root, True)
        self.assertEqual(report["captured_cases"], 1)
        self.assertFalse(report["library_tests_executed"])

    def test_analytic_formulas_and_invalid_tube(self):
        recipe = corpus.load_json(self.root / "recipes/part-block-001.json")
        self.assertAlmostEqual(corpus.analytic_measures(recipe)["volume_m3"], .000024)
        self.assertAlmostEqual(corpus.analytic_measures(recipe)["area_m2"], .0052)
        recipe = corpus.load_json(self.root / "recipes/part-tube-001.json")
        recipe["analytic"]["dimensions_m"]["inner_radius"] = .02
        with self.assertRaises(corpus.CorpusError):
            corpus.analytic_measures(recipe)

    def test_concave_profile_formula_and_remaining_legs(self):
        recipe = corpus.read_recipe(self.root,"recipes/part-concave-profile-001.json","part-concave-profile-001")
        result = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(result["volume_m3"],.000014)
        self.assertAlmostEqual(result["area_m2"],.0042)
        for name,value in (("vertical_leg_width",.04),("horizontal_leg_depth",.03)):
            changed = corpus.load_json(self.root / "recipes/part-concave-profile-001.json")
            changed["analytic"]["dimensions_m"][name] = value
            with self.assertRaisesRegex(corpus.CorpusError,"positive notch"):
                corpus.analytic_measures(changed)

    def test_polygon_rejects_crossing_touching_and_zero_area(self):
        for vertices in ([[0,0],[2,2],[0,2],[2,0]],
                         [[0,0],[2,0],[2,2],[1,0],[0,2]],
                         [[0,0],[1,0],[2,0]]):
            with self.assertRaises(corpus.CorpusError):
                corpus.check_polygon(vertices)
        recipe = corpus.read_recipe(self.root,"recipes/part-concave-profile-001.json","part-concave-profile-001")
        vertices = recipe["steps"][1]["parameters"]["vertices_m"]
        corpus.check_polygon(vertices[::-1])
        recipe["steps"][1]["parameters"]["vertices_m"] = [[0,0],[2,2],[0,2],[2,0]]
        self.write_json(self.root / "recipes/part-concave-profile-001.json",recipe)
        with self.assertRaisesRegex(corpus.CorpusError,"self-intersect"):
            corpus.read_recipe(self.root,"recipes/part-concave-profile-001.json","part-concave-profile-001")

    def test_frustum_analytic_measures_and_distinct_radii(self):
        recipe = corpus.read_recipe(self.root,"recipes/part-cone-frustum-001.json","part-cone-frustum-001")
        actual = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(actual["volume_m3"],3500*math.pi/3*1e-9,delta=1e-17)
        self.assertAlmostEqual(actual["area_m2"],math.pi*(125+75*math.sqrt(17))*1e-6,delta=1e-14)
        recipe["analytic"]["dimensions_m"]["top_radius"] = .01
        with self.assertRaisesRegex(corpus.CorpusError,"smaller positive top radius"):
            corpus.analytic_measures(recipe)

    def test_full_revolution_contract_and_profile_reference(self):
        relative = "recipes/part-cone-frustum-001.json"
        original = corpus.read_recipe(self.root,relative,"part-cone-frustum-001")
        self.assertEqual(original["steps"][-1]["operation"],"revolve")
        for mutation in ("partial","axis","origin","unknown-profile","wrong-plane"):
            recipe = copy.deepcopy(original)
            params = recipe["steps"][-1]["parameters"]
            if mutation=="partial":
                params["angle_rad"] = math.pi
            elif mutation=="axis":
                params["axis_direction"] = [1,0,0]
            elif mutation=="origin":
                params["axis_origin_m"] = [1,0,0]
            elif mutation=="unknown-profile":
                params["profiles"] = ["unknown-profile"]
            else:
                recipe["steps"][1]["parameters"]["plane"] = "XY"
            self.write_json(self.root / relative,recipe)
            with self.subTest(mutation=mutation), self.assertRaises(corpus.CorpusError):
                corpus.read_recipe(self.root,relative,"part-cone-frustum-001")

    def test_sector_formulas_include_both_radial_cuts(self):
        recipe = corpus.read_recipe(self.root,"recipes/part-cone-sector-001.json","part-cone-sector-001")
        result = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(result["volume_m3"],875*math.pi/3*1e-9,delta=1e-17)
        self.assertAlmostEqual(result["area_m2"],(math.pi*(125+75*math.sqrt(17))/4+300)*1e-6,delta=1e-14)

    def test_sector_angle_schema_and_construction_must_agree(self):
        relative = "recipes/part-cone-sector-001.json"
        original = corpus.read_recipe(self.root,relative,"part-cone-sector-001")
        for angle in (0,-1,2*math.pi,7):
            recipe = copy.deepcopy(original)
            recipe["analytic"]["angle_rad"] = angle
            self.write_json(self.root / relative,recipe)
            with self.subTest(angle=angle), self.assertRaises(corpus.CorpusError):
                corpus.read_recipe(self.root,relative,"part-cone-sector-001")
        recipe = copy.deepcopy(original)
        recipe["steps"][-1]["parameters"]["angle_rad"] = math.pi
        self.write_json(self.root / relative,recipe)
        with self.assertRaisesRegex(corpus.CorpusError,"construction angle differs"):
            corpus.read_recipe(self.root,relative,"part-cone-sector-001")
        recipe = copy.deepcopy(original)
        recipe["analytic"]["shape"] = "cone_frustum"
        with self.assertRaises(corpus.CorpusError):
            corpus.validate(self.root,"recipe",recipe)

    def test_sphere_formula_and_revolution_profile(self):
        relative = "recipes/part-sphere-001.json"
        original = corpus.read_recipe(self.root,relative,"part-sphere-001")
        measures = corpus.analytic_measures(original)
        self.assertAlmostEqual(measures["volume_m3"],4*math.pi*1e-6/3,delta=1e-17)
        self.assertAlmostEqual(measures["area_m2"],4*math.pi*1e-4,delta=1e-14)
        for mutation in ("radius","partial","half-plane"):
            recipe = copy.deepcopy(original)
            if mutation=="radius":
                recipe["steps"][1]["parameters"]["radius_m"] = .011
            elif mutation=="partial":
                recipe["steps"][-1]["parameters"]["angle_rad"] = math.pi
            else:
                recipe["steps"][1]["parameters"]["half_plane"] = "negative_x"
            self.write_json(self.root / relative,recipe)
            with self.subTest(mutation=mutation), self.assertRaises(corpus.CorpusError):
                corpus.read_recipe(self.root,relative,"part-sphere-001")

    def test_minor_sphere_cap_formulas_and_height_limit(self):
        recipe = corpus.read_recipe(self.root,"recipes/part-sphere-cap-001.json","part-sphere-cap-001")
        result = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(result["volume_m3"],625*math.pi/3*1e-9,delta=1e-17)
        self.assertAlmostEqual(result["area_m2"],175*math.pi*1e-6,delta=1e-14)
        recipe["analytic"]["dimensions_m"]["cap_height"] = .01
        with self.assertRaisesRegex(corpus.CorpusError,"height smaller than radius"):
            corpus.analytic_measures(recipe)

    def test_sphere_cap_construction_dimensions_must_match(self):
        relative = "recipes/part-sphere-cap-001.json"
        original = corpus.read_recipe(self.root,relative,"part-sphere-cap-001")
        for mutation in ("radius","height","partial"):
            recipe = copy.deepcopy(original)
            if mutation=="radius":
                recipe["steps"][1]["parameters"]["radius_m"] = .011
            elif mutation=="height":
                recipe["steps"][1]["parameters"]["cap_height_m"] = .004
            else:
                recipe["steps"][-1]["parameters"]["angle_rad"] = math.pi
            self.write_json(self.root / relative,recipe)
            with self.subTest(mutation=mutation), self.assertRaises(corpus.CorpusError):
                corpus.read_recipe(self.root,relative,"part-sphere-cap-001")

    def test_ring_torus_measures_and_ordered_radii(self):
        recipe = corpus.read_recipe(self.root,"recipes/part-torus-001.json","part-torus-001")
        actual = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(actual["volume_m3"],1000*math.pi**2*1e-9,delta=1e-17)
        self.assertAlmostEqual(actual["area_m2"],400*math.pi**2*1e-6,delta=1e-14)
        for minor in (.02,.025):
            recipe["analytic"]["dimensions_m"]["minor_radius"] = minor
            with self.subTest(minor=minor), self.assertRaisesRegex(corpus.CorpusError,"minor radius smaller"):
                corpus.analytic_measures(recipe)

    def test_torus_construction_radii_and_full_turn_must_match(self):
        relative = "recipes/part-torus-001.json"
        original = corpus.read_recipe(self.root,relative,"part-torus-001")
        for mutation in ("offset","radius","partial"):
            recipe = copy.deepcopy(original)
            if mutation=="offset":
                recipe["steps"][1]["parameters"]["radial_offset_m"] = .021
            elif mutation=="radius":
                recipe["steps"][1]["parameters"]["radius_m"] = .004
            else:
                recipe["steps"][-1]["parameters"]["angle_rad"] = math.pi
            self.write_json(self.root / relative,recipe)
            with self.subTest(mutation=mutation), self.assertRaises(corpus.CorpusError):
                corpus.read_recipe(self.root,relative,"part-torus-001")

    def test_size_corruption(self):
        self.make_case()
        (self.case / "source.sldprt").write_bytes(b"changed")
        with self.assertRaisesRegex(corpus.CorpusError, "size mismatch"):
            corpus.audit(self.root)

    def test_hash_corruption(self):
        self.make_case()
        path = self.case / "ref.x_b"
        path.write_bytes(b"X" * path.stat().st_size)
        with self.assertRaisesRegex(corpus.CorpusError, "hash mismatch"):
            corpus.audit(self.root)

    def test_native_wrong_volume(self):
        self.make_case()
        self.native["bodies"][0]["measurements_si"]["volume_m3"] *= 2
        self.update("native.json", self.native)
        with self.assertRaisesRegex(corpus.CorpusError, "analytic mismatch"):
            corpus.audit(self.root)

    def test_stale_revision(self):
        self.make_case()
        self.native["document_revision"] = "r2"
        self.update("native.json", self.native)
        with self.assertRaisesRegex(corpus.CorpusError, "revision differs"):
            corpus.audit(self.root)

    def test_missing_receipt(self):
        self.make_case()
        self.update("receipts.json", {"schema_version": 1, "exports": self.exports[:-1]})
        with self.assertRaisesRegex(corpus.CorpusError, "each reference export"):
            corpus.audit(self.root)

    def test_receipt_hash(self):
        self.make_case()
        self.exports[0]["sha256"] = "0" * 64
        self.update("receipts.json", {"schema_version": 1, "exports": self.exports})
        with self.assertRaisesRegex(corpus.CorpusError, "receipt sha256 mismatch"):
            corpus.audit(self.root)

    def test_receipt_unit_scale(self):
        self.make_case()
        self.exports[-1]["source_to_metre_scale"] = .001
        self.update("receipts.json", {"schema_version": 1, "exports": self.exports})
        with self.assertRaisesRegex(corpus.CorpusError, "unit/scale mismatch"):
            corpus.audit(self.root)

    def test_protocol_is_separate_from_file_format(self):
        self.make_case()
        del self.exports[-1]["application_protocol"]
        self.exports[-1]["format_version"] = "AP214"
        self.update("receipts.json", {"schema_version": 1, "exports": self.exports})
        with self.assertRaises(corpus.CorpusError):
            corpus.audit(self.root)

    def test_receipt_configuration(self):
        self.make_case()
        self.exports[0]["configuration"] = "Other"
        self.update("receipts.json", {"schema_version": 1, "exports": self.exports})
        with self.assertRaisesRegex(corpus.CorpusError, "configuration differs"):
            corpus.audit(self.root)

    def test_unlisted_artifact(self):
        self.make_case()
        (self.case / "unexpected.sldprt").write_bytes(b"unexpected")
        with self.assertRaisesRegex(corpus.CorpusError, "unlisted"):
            corpus.audit(self.root)

    def test_paths_and_symlinks(self):
        self.make_case()
        for path in ("../plan.json", "/etc/passwd", "C:\\data\\file"):
            with self.subTest(path=path), self.assertRaises(corpus.CorpusError):
                corpus.local_file(self.case, path)
        (self.case / "link").symlink_to(self.root / "plan.json")
        with self.assertRaisesRegex(corpus.CorpusError, "symlink"):
            corpus.local_file(self.case, "link")

    def test_unsupported_requires_issue_and_error(self):
        self.make_case()
        self.manifest["expectations"]["step"]["outcome"] = "unsupported"
        self.save()
        with self.assertRaises(corpus.CorpusError):
            corpus.audit(self.root)

    def test_ambiguous_and_nonfinite_json(self):
        path = self.root / "bad.json"
        for value in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":1e999}'):
            with self.subTest(value=value):
                path.write_text(value)
                with self.assertRaises(corpus.CorpusError):
                    corpus.load_json(path)

    def test_blind_hole_analytic_measures(self):
        recipe = corpus.load_json(self.root / "recipes/part-blind-hole-001.json")
        measures = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(measures["volume_m3"], 1750*math.pi*1e-9, delta=1e-17)
        self.assertAlmostEqual(measures["area_m2"], 700*math.pi*1e-6, delta=1e-14)

    def test_blind_hole_requires_remaining_floor_and_wall(self):
        for field,value in (("hole_depth",.02), ("hole_depth",.03), ("inner_radius",.01)):
            with self.subTest(field=field, value=value):
                recipe = corpus.load_json(self.root / "recipes/part-blind-hole-001.json")
                recipe["analytic"]["dimensions_m"][field] = value
                with self.assertRaisesRegex(corpus.CorpusError, "remaining floor"):
                    corpus.analytic_measures(recipe)

    def test_cut_before_solid_is_rejected(self):
        path = self.root / "recipes/part-blind-hole-001.json"
        recipe = corpus.load_json(path)
        create, outer, base, hole, cut = recipe["steps"]
        recipe["steps"] = [create, hole, cut, outer, base]
        self.write_json(path, recipe)
        with self.assertRaisesRegex(corpus.CorpusError, "earlier solid-body"):
            corpus.audit(self.root)

    def test_through_hole_analytic_measures(self):
        recipe = corpus.load_json(self.root / "recipes/part-through-hole-001.json")
        measures = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(measures["volume_m3"], (24000-1000*math.pi)*1e-9, delta=1e-17)
        self.assertAlmostEqual(measures["area_m2"], (5200+350*math.pi)*1e-6, delta=1e-14)

    def test_through_bore_requires_closed_side_clearance(self):
        for field,value in (("bore_radius",.01),("bore_x",.005),("bore_y",.026)):
            with self.subTest(field=field, value=value):
                recipe = corpus.load_json(self.root / "recipes/part-through-hole-001.json")
                recipe["analytic"]["dimensions_m"][field] = value
                with self.assertRaisesRegex(corpus.CorpusError, "positive clearance"):
                    corpus.analytic_measures(recipe)

    def test_through_all_forbids_ambiguous_depth_and_boss(self):
        for mutation in ("depth","boss"):
            with self.subTest(mutation=mutation):
                recipe = corpus.load_json(self.root / "recipes/part-through-hole-001.json")
                cut = recipe["steps"][-1]["parameters"]
                if mutation == "depth":
                    cut["height_m"] = .04
                else:
                    cut["operation"] = "new_body"
                with self.assertRaises(corpus.CorpusError):
                    corpus.validate(self.root, "recipe", recipe)

    def test_stepped_bore_analytic_measures(self):
        recipe = corpus.load_json(self.root / "recipes/part-stepped-bore-001.json")
        measures = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(measures["volume_m3"],1604*math.pi*1e-9,delta=1e-17)
        self.assertAlmostEqual(measures["area_m2"],750*math.pi*1e-6,delta=1e-14)

    def test_stepped_bore_requires_ordered_radii_and_shoulder(self):
        for field,value in (("bore_radius",.006),("counterbore_radius",.01),("counterbore_depth",.02)):
            with self.subTest(field=field,value=value):
                recipe = corpus.load_json(self.root / "recipes/part-stepped-bore-001.json")
                recipe["analytic"]["dimensions_m"][field] = value
                with self.assertRaisesRegex(corpus.CorpusError,"ordered radii"):
                    corpus.analytic_measures(recipe)

    def test_two_holes_analytic_measures(self):
        recipe = corpus.load_json(self.root / "recipes/part-two-holes-001.json")
        measures = corpus.analytic_measures(recipe)
        self.assertAlmostEqual(measures["volume_m3"],(24000-360*math.pi)*1e-9,delta=1e-17)
        self.assertAlmostEqual(measures["area_m2"],(5200+204*math.pi)*1e-6,delta=1e-14)

    def test_two_holes_require_clearance_and_separation(self):
        for field,value in (("first_x",.003),("first_y",.002),("second_x",.016),("second_x",.015),("second_x",.01)):
            with self.subTest(field=field,value=value):
                recipe = corpus.load_json(self.root / "recipes/part-two-holes-001.json")
                recipe["analytic"]["dimensions_m"][field] = value
                with self.assertRaisesRegex(corpus.CorpusError,"clearance|separated"):
                    corpus.analytic_measures(recipe)

    def test_missing_recipe_parameter(self):
        path = self.root / "recipes/part-cylinder-001.json"
        recipe = corpus.load_json(path)
        del recipe["steps"][1]["parameters"]["radius_m"]
        self.write_json(path, recipe)
        with self.assertRaises(corpus.CorpusError):
            corpus.audit(self.root)

    def test_unknown_recipe_profile(self):
        path = self.root / "recipes/part-cylinder-001.json"
        recipe = corpus.load_json(path)
        recipe["steps"][-1]["parameters"]["profiles"] = ["missing-profile"]
        self.write_json(path, recipe)
        with self.assertRaisesRegex(corpus.CorpusError, "unknown or later sketch"):
            corpus.audit(self.root)


class CapturedCylinderTest(unittest.TestCase):
    def test_admitted_cylinder_integrity(self):
        report = corpus.audit(ROOT, require_ready=True)
        self.assertIn("part-cylinder-001", {case["id"] for case in report["cases"]})

    def test_native_samples_match_construction(self):
        native = corpus.load_json(ROOT / "cases/part-cylinder-001/reference/native.json")
        brep = native["observations"]["brep"]["entities"]
        count = 0
        for label, evaluated in native["observations"]["evaluations"].items():
            entity = brep[int(label.split("-")[-1])]
            for sample in evaluated["samples"]:
                x,y,z = sample["position"]
                if entity["geometry"]["type"] in ("circle", "cylinder"):
                    self.assertAlmostEqual((x*x+y*y)**.5, .01, delta=1e-12)
                else:
                    self.assertAlmostEqual(z, entity["geometry"]["origin"][2], delta=1e-12)
                self.assertGreaterEqual(z, -1e-12)
                self.assertLessEqual(z, .02+1e-12)
                count += 1
        self.assertEqual(count, 26)


class CapturedBlockTest(unittest.TestCase):
    def test_admitted_block_integrity(self):
        report = corpus.audit(ROOT, require_ready=True)
        self.assertIn("part-block-001", {case["id"] for case in report["cases"]})

    def test_native_block_samples_match_lines_and_planes(self):
        native = corpus.load_json(ROOT / "cases/part-block-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"], {"faces": 6, "edges": 12, "vertices": 8, "shells": 1})
        self.assertAlmostEqual(body["measurements_si"]["volume_m3"], .000024, delta=1e-16)
        self.assertAlmostEqual(body["measurements_si"]["area_m2"], .0052, delta=1e-14)
        entities = native["observations"]["brep"]["entities"]
        count = 0
        for label, evaluated in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluated["samples"]:
                point = sample["position"]
                for coordinate, maximum in zip(point, (.02,.03,.04)):
                    self.assertGreaterEqual(coordinate, -1e-12)
                    self.assertLessEqual(coordinate, maximum+1e-12)
                if entity["kind"] == "curve":
                    target = [o+d*sample["parameter"] for o,d in
                              zip(geometry["origin"], geometry["direction"])]
                    for actual, expected in zip(point, target):
                        self.assertAlmostEqual(actual, expected, delta=1e-12)
                else:
                    residual = sum((x-o)*n for x,o,n in zip(
                        point, geometry["origin"], geometry["normal"]))
                    self.assertAlmostEqual(residual, 0, delta=1e-12)
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                count += 1
        self.assertEqual(count, 90)


class CapturedTubeTest(unittest.TestCase):
    def test_admitted_tube_integrity(self):
        report = corpus.audit(ROOT, require_ready=True)
        self.assertIn("part-tube-001", {case["id"] for case in report["cases"]})

    def test_native_tube_samples_preserve_bore_and_normals(self):
        native = corpus.load_json(ROOT / "cases/part-tube-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"], {"faces": 4, "edges": 4, "vertices": 0, "shells": 1})
        self.assertAlmostEqual(body["measurements_si"]["volume_m3"],
                               1500*math.pi*1e-9, delta=1e-16)
        self.assertAlmostEqual(body["measurements_si"]["area_m2"],
                               750*math.pi*1e-6, delta=1e-14)
        entities = native["observations"]["brep"]["entities"]
        count = 0
        for label, evaluated in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluated["samples"]:
                x,y,z = sample["position"]
                radius = math.hypot(x,y)
                self.assertGreaterEqual(radius, .005-1e-12)
                self.assertLessEqual(radius, .01+1e-12)
                self.assertGreaterEqual(z, -1e-12)
                self.assertLessEqual(z, .02+1e-12)
                if entity["kind"] == "curve" or geometry["type"] == "cylinder":
                    self.assertAlmostEqual(radius, geometry["radius"], delta=1e-12)
                else:
                    self.assertAlmostEqual(z, geometry["origin"][2], delta=1e-12)
                if entity["kind"] == "surface":
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    if geometry["type"] == "cylinder":
                        normal = sample["face_normal"]
                        radial_dot = x*normal[0]+y*normal[1]
                        if geometry["radius"] < .0075:
                            self.assertLess(radial_dot, 0)
                        else:
                            self.assertGreater(radial_dot, 0)
                count += 1
        self.assertEqual(count, 46)


class CapturedBlindHoleTest(unittest.TestCase):
    def test_admitted_blind_hole_integrity(self):
        report = corpus.audit(ROOT, require_ready=True)
        self.assertIn("part-blind-hole-001", {case["id"] for case in report["cases"]})

    def test_native_floor_entry_and_normals(self):
        native = corpus.load_json(ROOT / "cases/part-blind-hole-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"], {"faces": 5, "edges": 4, "vertices": 0, "shells": 1})
        # Common pi factors cancel: stock center Z=10 mm, removed center Z=15 mm.
        expected_z = (2000*.01-250*.015)/(2000-250)
        self.assertAlmostEqual(body["measurements_si"]["centroid_m"][2], expected_z, delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        count = 0
        for label,evaluated in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluated["samples"]:
                x,y,z = sample["position"]
                radius = math.hypot(x,y)
                self.assertLessEqual(radius, .01+1e-12)
                self.assertGreaterEqual(z, -1e-12)
                self.assertLessEqual(z, .02+1e-12)
                if entity["kind"] == "curve" or geometry["type"] == "cylinder":
                    self.assertAlmostEqual(radius, geometry["radius"], delta=1e-12)
                    if geometry["radius"] < .0075:
                        self.assertGreaterEqual(z, .01-1e-12)
                if entity["kind"] == "curve":
                    self.assertAlmostEqual(z, geometry["center"][2], delta=1e-12)
                else:
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    normal = sample["face_normal"]
                    if geometry["type"] == "cylinder":
                        radial_dot = x*normal[0]+y*normal[1]
                        if geometry["radius"] < .0075:
                            self.assertLess(radial_dot, 0)
                        else:
                            self.assertGreater(radial_dot, 0)
                    else:
                        self.assertAlmostEqual(z, geometry["origin"][2], delta=1e-12)
                        if abs(z-.01) < 1e-12:
                            self.assertLessEqual(radius, .005+1e-12)
                        if abs(z-.02) < 1e-12:
                            self.assertGreaterEqual(radius, .005-1e-12)
                        if z > 1e-12:
                            self.assertGreater(normal[2], 0)
                        else:
                            self.assertLess(normal[2], 0)
                count += 1
        self.assertEqual(count, 51)


class CapturedThroughHoleTest(unittest.TestCase):
    def test_admitted_through_hole_integrity(self):
        report = corpus.audit(ROOT, require_ready=True)
        self.assertIn("part-through-hole-001", {case["id"] for case in report["cases"]})

    def test_native_through_hole_position_and_normals(self):
        native = corpus.load_json(ROOT / "cases/part-through-hole-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"], {"faces":7,"edges":14,"vertices":8,"shells":1})
        for actual,expected in zip(body["measurements_si"]["centroid_m"],(.01,.015,.02)):
            self.assertAlmostEqual(actual,expected,delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        count = 0
        for label,evaluated in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluated["samples"]:
                point = sample["position"]
                x,y,z = point
                radius = math.hypot(x-.01,y-.015)
                for coordinate,maximum in zip(point,(.02,.03,.04)):
                    self.assertGreaterEqual(coordinate,-1e-12)
                    self.assertLessEqual(coordinate,maximum+1e-12)
                self.assertGreaterEqual(radius,.005-1e-12)
                if entity["kind"] == "curve":
                    if geometry["type"] == "line":
                        target = [o+d*sample["parameter"] for o,d in zip(
                            geometry["origin"],geometry["direction"])]
                        self.assertLess(math.dist(point,target),1e-12)
                    else:
                        self.assertAlmostEqual(radius,.005,delta=1e-12)
                        self.assertAlmostEqual(z,geometry["center"][2],delta=1e-12)
                else:
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    normal = sample["face_normal"]
                    if geometry["type"] == "cylinder":
                        self.assertAlmostEqual(radius,.005,delta=1e-12)
                        self.assertLess((x-.01)*normal[0]+(y-.015)*normal[1],0)
                    else:
                        residual = sum((a-o)*n for a,o,n in zip(point,geometry["origin"],geometry["normal"]))
                        self.assertAlmostEqual(residual,0,delta=1e-12)
                        axis = max(range(3),key=lambda i:abs(geometry["normal"][i]))
                        if point[axis] > 1e-12:
                            self.assertGreater(normal[axis],0)
                        else:
                            self.assertLess(normal[axis],0)
                count += 1
        self.assertEqual(count,108)


class CapturedSteppedBoreTest(unittest.TestCase):
    def test_admitted_stepped_bore_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-stepped-bore-001",{case["id"] for case in report["cases"]})

    def test_reopen_identifiers_come_from_raw_responses(self):
        for case_id in ("part-through-hole-001","part-stepped-bore-001"):
            with self.subTest(case=case_id):
                capture = corpus.load_json(ROOT / "cases" / case_id / "provenance/capture.json")
                events = {event["step"]:event for event in capture["events"]}
                opened = events["reopen-source"]["response"]["result"]["structuredContent"]["result"]
                self.assertEqual(capture["recipe_mapping"]["reopen"]["reopened_document"],opened["doc_id"])

    def test_native_bands_shoulder_and_normals(self):
        native = corpus.load_json(ROOT / "cases/part-stepped-bore-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":6,"edges":6,"vertices":0,"shells":1})
        self.assertAlmostEqual(body["measurements_si"]["centroid_m"][2],14744/1604*.001,delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        count = 0
        for label,evaluated in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluated["samples"]:
                x,y,z = sample["position"]
                radius = math.hypot(x,y)
                self.assertGreaterEqual(radius,.003-1e-12)
                self.assertLessEqual(radius,.01+1e-12)
                self.assertGreaterEqual(z,-1e-12)
                self.assertLessEqual(z,.02+1e-12)
                if entity["kind"] == "curve" or geometry["type"] == "cylinder":
                    self.assertAlmostEqual(radius,geometry["radius"],delta=1e-12)
                    if abs(radius-.003) < 1e-12:
                        self.assertLessEqual(z,.012+1e-12)
                    if abs(radius-.006) < 1e-12:
                        self.assertGreaterEqual(z,.012-1e-12)
                if entity["kind"] == "curve":
                    self.assertAlmostEqual(z,geometry["center"][2],delta=1e-12)
                else:
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    normal = sample["face_normal"]
                    if geometry["type"] == "cylinder":
                        radial_dot = x*normal[0]+y*normal[1]
                        if abs(geometry["radius"]-.01) < 1e-12:
                            self.assertGreater(radial_dot,0)
                        else:
                            self.assertLess(radial_dot,0)
                    else:
                        self.assertAlmostEqual(z,geometry["origin"][2],delta=1e-12)
                        if abs(z-.012) < 1e-12:
                            self.assertLessEqual(radius,.006+1e-12)
                        if abs(z-.02) < 1e-12:
                            self.assertGreaterEqual(radius,.006-1e-12)
                        if z > 1e-12:
                            self.assertGreater(normal[2],0)
                        else:
                            self.assertLess(normal[2],0)
                count += 1
        self.assertEqual(count,69)


class CapturedTwoHolesTest(unittest.TestCase):
    def test_admitted_two_holes_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-two-holes-001",{case["id"] for case in report["cases"]})

    def test_native_hole_ownership_caps_and_normals(self):
        native = corpus.load_json(ROOT / "cases/part-two-holes-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":8,"edges":16,"vertices":8,"shells":1})
        for a,b in zip(body["measurements_si"]["centroid_m"],(.02,.015,.01)):
            self.assertAlmostEqual(a,b,delta=1e-12)
        centers = ((.01,.015),(.03,.015))
        entities = native["observations"]["brep"]["entities"]
        owners,count = set(),0
        for label,evaluated in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluated["samples"]:
                point = sample["position"]
                x,y,z = point
                for coordinate,maximum in zip(point,(.04,.03,.02)):
                    self.assertGreaterEqual(coordinate,-1e-12)
                    self.assertLessEqual(coordinate,maximum+1e-12)
                for cx,cy in centers:
                    self.assertGreaterEqual(math.hypot(x-cx,y-cy),.003-1e-12)
                if entity["kind"] == "curve":
                    if geometry["type"] == "line":
                        target = [o+d*sample["parameter"] for o,d in zip(geometry["origin"],geometry["direction"])]
                        self.assertLess(math.dist(point,target),1e-12)
                    else:
                        self.assertAlmostEqual(math.dist(point[:2],geometry["center"][:2]),.003,delta=1e-12)
                        self.assertAlmostEqual(z,geometry["center"][2],delta=1e-12)
                else:
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    normal = sample["face_normal"]
                    if geometry["type"] == "cylinder":
                        center = geometry["origin"][:2]
                        matches = [c for c in centers if math.dist(center,c) < 1e-12]
                        self.assertEqual(len(matches),1)
                        owners.add(matches[0])
                        self.assertAlmostEqual(math.dist(point[:2],center),.003,delta=1e-12)
                        self.assertLess((x-center[0])*normal[0]+(y-center[1])*normal[1],0)
                    else:
                        self.assertAlmostEqual(sum((a-o)*n for a,o,n in zip(point,geometry["origin"],geometry["normal"])),0,delta=1e-12)
                        axis = max(range(3),key=lambda i:abs(geometry["normal"][i]))
                        if point[axis] > 1e-12:
                            self.assertGreater(normal[axis],0)
                        else:
                            self.assertLess(normal[axis],0)
                count += 1
        self.assertEqual(owners,set(centers))
        self.assertEqual(count,126)


class CapturedConcaveProfileTest(unittest.TestCase):
    def test_admitted_concave_profile_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-concave-profile-001",{c["id"] for c in report["cases"]})

    def test_native_concave_trims_and_material_normals(self):
        native = corpus.load_json(ROOT / "cases/part-concave-profile-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":8,"edges":18,"vertices":12,"shells":1})
        for a,b in zip(body["measurements_si"]["centroid_m"],(.014642857142857143,.011428571428571429,.01)):
            self.assertAlmostEqual(a,b,delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        count=inside=outside=0
        cap_memberships = {}
        for label,evaluation in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            geometry = entity["geometry"]
            for sample in evaluation["samples"]:
                point = sample["position"]
                x,y,z = point
                for value,maximum in zip(point,(.04,.03,.02)):
                    self.assertGreaterEqual(value,-1e-12)
                    self.assertLessEqual(value,maximum+1e-12)
                expected = x<=.015+1e-12 or y<=.01+1e-12
                if entity["kind"] == "curve":
                    self.assertTrue(expected)
                    self.assertEqual(geometry["type"],"line")
                    target = [o+d*sample["parameter"] for o,d in zip(geometry["origin"],geometry["direction"])]
                    self.assertLess(math.dist(point,target),1e-12)
                else:
                    self.assertEqual(geometry["type"],"plane")
                    self.assertEqual(sample["trim_membership"]["geometric_inside_or_boundary"],expected)
                    self.assertAlmostEqual(sum((a-o)*n for a,o,n in zip(point,geometry["origin"],geometry["normal"])),0,delta=1e-12)
                    inside += int(expected)
                    outside += int(not expected)
                    axis = max(range(3),key=lambda i:abs(geometry["normal"][i]))
                    expected_normal = [0,0,0]
                    expected_normal[axis] = -1 if abs(point[axis])<1e-12 else 1
                    self.assertLess(math.dist(sample["face_normal"],expected_normal),1e-12)
                    if axis==2:
                        cap_memberships.setdefault(round(z,6),[]).append(expected)
                count += 1
        self.assertEqual((count,inside,outside),(138,40,8))
        self.assertEqual(set(cap_memberships),{0,.02})
        for values in cap_memberships.values():
            self.assertEqual((values.count(True),values.count(False)),(5,4))


class MultipleSolidsContractTest(unittest.TestCase):
    def setUp(self):
        self.case = ROOT / "cases/part-multiple-solids-001"
        self.manifest = corpus.load_json(self.case / "case.json")
        self.native = corpus.load_json(self.case / "reference/native.json")
        self.recipe = corpus.read_recipe(ROOT,self.manifest["recipe"],self.manifest["id"])

    def test_admitted_multiple_solids_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-multiple-solids-001",{c["id"] for c in report["cases"]})

    def test_individual_and_document_measures(self):
        measures = corpus.multiple_solid_measures(self.recipe)
        self.assertAlmostEqual(measures["large-block"]["volume_m3"],.000024)
        self.assertAlmostEqual(measures["small-block"]["volume_m3"],.000003)
        total = corpus.analytic_measures(self.recipe)
        self.assertAlmostEqual(total["volume_m3"],.000027)
        self.assertAlmostEqual(total["area_m2"],.0065)
        for actual,expected in zip(total["centroid_m"],(.015,.014166666666666666,.01888888888888889)):
            self.assertAlmostEqual(actual,expected,delta=1e-12)

    def test_body_selection_is_independent_of_native_order(self):
        self.native["bodies"].reverse()
        selected = corpus.selected_bodies(self.manifest["selection"],self.native)
        self.assertEqual([(e["body_id"],b["key"]) for e,b in selected],
                         [(6,"large-block"),(2,"small-block")])
        corpus.check_native(self.manifest,self.native,self.recipe)

    def test_duplicate_or_incomplete_body_mapping_is_rejected(self):
        original = self.manifest["selection"]
        for mutation in ("duplicate-id","duplicate-key","missing","unknown-key"):
            selection = copy.deepcopy(original)
            entries = selection["bodies"]
            if mutation=="duplicate-id":
                entries[1]["body_id"] = entries[0]["body_id"]
            elif mutation=="duplicate-key":
                entries[1]["native_body_key"] = entries[0]["native_body_key"]
            elif mutation=="missing":
                entries.pop()
            else:
                entries[1]["native_body_key"] = "unobserved-body"
            with self.subTest(mutation=mutation), self.assertRaisesRegex(corpus.CorpusError,"uniquely cover"):
                corpus.selected_bodies(selection,self.native)

    def test_single_body_selection_cannot_stand_for_two_bodies(self):
        selection = self.manifest["selection"]
        selection.pop("bodies")
        selection["body_id"] = 2
        with self.assertRaisesRegex(corpus.CorpusError,"exactly one native body"):
            corpus.check_native(self.manifest,self.native,self.recipe)

    def test_ambiguous_selection_schema_is_rejected(self):
        self.manifest["selection"]["body_id"] = 2
        with self.assertRaises(corpus.CorpusError):
            corpus.validate(ROOT,"case",self.manifest)

    def test_document_only_and_compensated_wrong_body_measures_are_rejected(self):
        self.native["bodies"][0]["measurements_si"]["volume_m3"] += .000001
        self.native["bodies"][1]["measurements_si"]["volume_m3"] -= .000001
        with self.assertRaisesRegex(corpus.CorpusError,"analytic mismatch"):
            corpus.check_native(self.manifest,self.native,self.recipe)

    def test_missing_document_measurements_are_rejected(self):
        self.native.pop("document_measurements_si")
        with self.assertRaisesRegex(corpus.CorpusError,"require document measures"):
            corpus.check_native(self.manifest,self.native,self.recipe)

    def test_missing_explicit_selection_is_rejected(self):
        self.manifest.pop("selection")
        with self.assertRaisesRegex(corpus.CorpusError,"require explicit body selections"):
            corpus.check_native(self.manifest,self.native,self.recipe)

    def test_shifted_small_body_centroid_is_rejected(self):
        self.native["bodies"][1]["measurements_si"]["centroid_m"][0] += .001
        with self.assertRaisesRegex(corpus.CorpusError,"centroid mismatch"):
            corpus.check_native(self.manifest,self.native,self.recipe)

    def test_native_samples_preserve_body_ownership(self):
        observations = self.native["observations"]
        entities = observations["brep"]["entities"]
        byref = {e["ref"]:e for e in entities}
        boxes = {m["body_measurements"][0]["ref"]:m["bounding_box"] for m in observations["body_measurements"]}
        body_counts = {ref:0 for ref in boxes}
        for label,evaluation in observations["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            owner = byref[entity["owner"]]
            ref = owner["body"]
            box = boxes[ref]
            g = entity["geometry"]
            for sample in evaluation["samples"]:
                point = sample["position"]
                for a,value,b in zip(box["min"],point,box["max"]):
                    self.assertGreaterEqual(value,a-1e-12)
                    self.assertLessEqual(value,b+1e-12)
                if entity["kind"]=="curve":
                    self.assertEqual(g["type"],"line")
                    self.assertLess(math.dist(point,[o+d*sample["parameter"] for o,d in zip(g["origin"],g["direction"])]),1e-12)
                else:
                    self.assertEqual(g["type"],"plane")
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    self.assertAlmostEqual(sum((a-o)*n for a,o,n in zip(point,g["origin"],g["normal"])),0,delta=1e-12)
                    axis = max(range(3),key=lambda i:abs(g["normal"][i]))
                    expected = [0,0,0]
                    expected[axis] = -1 if abs(point[axis]-box["min"][axis])<1e-12 else 1
                    self.assertLess(math.dist(expected,sample["face_normal"]),1e-12)
                body_counts[ref] += 1
        self.assertEqual(sorted(body_counts.values()),[90,90])


class CapturedThinWallTest(unittest.TestCase):
    def test_admitted_thin_wall_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-thin-wall-001",{c["id"] for c in report["cases"]})

    def test_minimum_feature_and_analytic_measures(self):
        recipe = corpus.read_recipe(ROOT,"recipes/part-thin-wall-001.json","part-thin-wall-001")
        self.assertEqual(recipe["steps"][-1]["parameters"]["height_m"],1e-5)
        self.assertEqual(min(recipe["analytic"]["dimensions_m"].values()),1e-5)
        self.assertAlmostEqual(corpus.analytic_measures(recipe)["volume_m3"],6e-9,delta=1e-20)
        self.assertAlmostEqual(corpus.analytic_measures(recipe)["area_m2"],.001201,delta=1e-15)
        case = ROOT / "cases/part-thin-wall-001"
        manifest = corpus.load_json(case / "case.json")
        observations = corpus.load_json(case / "validation/observations.json")
        tolerance = manifest["tolerances"]["length_absolute_m"]
        self.assertEqual(tolerance,1e-8)
        self.assertEqual(observations["minimum_feature_size_m"],1e-5)
        self.assertEqual(observations["binding_tolerance_m"],tolerance)
        self.assertAlmostEqual(observations["feature_to_tolerance_ratio"],1e-5/tolerance)

    def test_native_short_edges_caps_and_material_normals(self):
        native = corpus.load_json(ROOT / "cases/part-thin-wall-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":6,"edges":12,"vertices":8,"shells":1})
        for actual,expected in zip(body["measurements_si"]["centroid_m"],(.01,.015,5e-6)):
            self.assertAlmostEqual(actual,expected,delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        self.assertEqual(sorted(round(e["position"][2],12) for e in entities if e["kind"]=="vertex"),
                         [0]*4+[1e-5]*4)
        count=short_edges=0
        cap_normals = set()
        for label,evaluation in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            g = entity["geometry"]
            if entity["kind"]=="curve" and abs(g["direction"][2])>.9:
                short_edges += 1
                zs = [sample["position"][2] for sample in evaluation["samples"]]
                self.assertAlmostEqual(max(zs)-min(zs),1e-5,delta=1e-12)
            for sample in evaluation["samples"]:
                point = sample["position"]
                for value,maximum in zip(point,(.02,.03,1e-5)):
                    self.assertGreaterEqual(value,-1e-12)
                    self.assertLessEqual(value,maximum+1e-12)
                if entity["kind"]=="curve":
                    self.assertEqual(g["type"],"line")
                    self.assertLess(math.dist(point,[o+d*sample["parameter"] for o,d in zip(g["origin"],g["direction"])]),1e-12)
                else:
                    self.assertEqual(g["type"],"plane")
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    self.assertAlmostEqual(sum((a-o)*n for a,o,n in zip(point,g["origin"],g["normal"])),0,delta=1e-12)
                    axis = max(range(3),key=lambda i:abs(g["normal"][i]))
                    expected = [0,0,0]
                    expected[axis] = -1 if abs(point[axis])<1e-12 else 1
                    self.assertLess(math.dist(expected,sample["face_normal"]),1e-12)
                    if axis==2:
                        cap_normals.add((round(point[2],12),expected[2]))
                count += 1
        self.assertEqual(count,90)
        self.assertEqual(short_edges,4)
        self.assertEqual(cap_normals,{(0,-1),(1e-5,1)})


class CapturedConeFrustumTest(unittest.TestCase):
    def test_admitted_frustum_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-cone-frustum-001",{c["id"] for c in report["cases"]})

    def test_native_frustum_radius_law_and_material_normals(self):
        native = corpus.load_json(ROOT / "cases/part-cone-frustum-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":3,"edges":2,"vertices":0,"shells":1})
        for actual,expected in zip(body["measurements_si"]["centroid_m"],(0,0,.055/7)):
            self.assertAlmostEqual(actual,expected,delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        cone = next(e["geometry"] for e in entities if e["kind"]=="surface" and e["geometry"]["type"]=="cone")
        self.assertAlmostEqual(cone["half_angle"],math.atan(.25),delta=1e-12)
        count=mantle_samples=0
        cap_normals = set()
        for label,evaluation in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            g = entity["geometry"]
            for sample in evaluation["samples"]:
                x,y,z = sample["position"]
                radius = math.hypot(x,y)
                self.assertGreaterEqual(z,-1e-12)
                self.assertLessEqual(z,.02+1e-12)
                self.assertLessEqual(radius,.01-.25*z+1e-12)
                if entity["kind"]=="curve":
                    self.assertEqual(g["type"],"circle")
                    self.assertAlmostEqual(radius,g["radius"],delta=1e-12)
                    self.assertAlmostEqual(z,g["center"][2],delta=1e-12)
                else:
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    if g["type"]=="cone":
                        self.assertAlmostEqual(radius,.01-.25*z,delta=1e-12)
                        expected = [x/radius/math.sqrt(1+.25**2),y/radius/math.sqrt(1+.25**2),.25/math.sqrt(1+.25**2)]
                        mantle_samples += 1
                    else:
                        self.assertEqual(g["type"],"plane")
                        self.assertAlmostEqual(z,g["origin"][2],delta=1e-12)
                        expected = [0,0,-1 if abs(z)<1e-12 else 1]
                        cap_normals.add((round(z,6),expected[2]))
                    self.assertLess(math.dist(sample["face_normal"],expected),1e-12)
                count += 1
        self.assertEqual((count,mantle_samples),(28,8))
        self.assertEqual(cap_normals,{(0,-1),(.02,1)})


class CapturedConeSectorTest(unittest.TestCase):
    def test_admitted_sector_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-cone-sector-001",{c["id"] for c in report["cases"]})

    def test_native_arc_intervals_cut_normals_and_trim_membership(self):
        native = corpus.load_json(ROOT / "cases/part-cone-sector-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":5,"edges":9,"vertices":6,"shells":1})
        for actual,expected in zip(body["measurements_si"]["centroid_m"],(.075/(7*math.pi),.075/(7*math.pi),.055/7)):
            self.assertAlmostEqual(actual,expected,delta=1e-12)
        entities = native["observations"]["brep"]["entities"]
        byref = {e["ref"]:e for e in entities}
        arcs = []
        for entity in entities:
            if entity["kind"]=="curve" and entity["geometry"]["type"]=="circle":
                # Holding circles are closed; their topological edges are arcs.
                self.assertTrue(entity["geometry"]["closed"])
                edge = byref[entity["owner"]]
                self.assertAlmostEqual(abs(edge["curve_interval"][1]-edge["curve_interval"][0]),math.pi/2,delta=1e-12)
                self.assertNotEqual(edge["start_vertex"],edge["end_vertex"])
                arcs.append(entity["geometry"]["radius"])
        self.assertEqual(sorted(arcs),[.005,.01])
        count=inside=outside=0
        cut_normals = set()
        for label,evaluation in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            g = entity["geometry"]
            for sample in evaluation["samples"]:
                point = sample["position"]
                x,y,z = point
                radius = math.hypot(x,y)
                expected_inside = x>=-1e-12 and y>=-1e-12 and -1e-12<=z<=.02+1e-12 and radius<=.01-.25*z+1e-12
                if entity["kind"]=="curve":
                    self.assertTrue(expected_inside)
                    if g["type"]=="circle":
                        self.assertAlmostEqual(radius,g["radius"],delta=1e-12)
                        self.assertAlmostEqual(z,g["center"][2],delta=1e-12)
                    else:
                        self.assertLess(math.dist(point,[o+d*sample["parameter"] for o,d in zip(g["origin"],g["direction"])]),1e-12)
                else:
                    self.assertEqual(sample["trim_membership"]["geometric_inside_or_boundary"],expected_inside)
                    inside += int(expected_inside)
                    outside += int(not expected_inside)
                    if g["type"]=="cone":
                        self.assertAlmostEqual(radius,.01-.25*z,delta=1e-12)
                        normal = [x/radius/math.sqrt(1+.25**2),y/radius/math.sqrt(1+.25**2),.25/math.sqrt(1+.25**2)]
                    else:
                        self.assertAlmostEqual(sum((a-o)*n for a,o,n in zip(point,g["origin"],g["normal"])),0,delta=1e-12)
                        axis = max(range(3),key=lambda a:abs(g["normal"][a]))
                        normal = [0,0,0]
                        normal[axis] = 1 if axis==2 and z>.01 else -1
                        if axis!=2:
                            cut_normals.add(tuple(normal))
                    self.assertLess(math.dist(sample["face_normal"],normal),1e-12)
                count += 1
        self.assertEqual((count,inside,outside),(73,24,4))
        self.assertEqual(cut_normals,{(-1,0,0),(0,-1,0)})


class CapturedSphereTest(unittest.TestCase):
    def test_admitted_sphere_preserves_unsupported_step_expectation(self):
        corpus.audit(ROOT,require_ready=True)
        case = ROOT / "cases/part-sphere-001"
        manifest = corpus.load_json(case / "case.json")
        self.assertEqual(manifest["expectations"]["step"]["outcome"],"unsupported")
        self.assertEqual(manifest["expectations"]["step"]["error_code"],"unsupported_format")
        error = corpus.load_json(case / "validation/export-error.json")
        self.assertEqual(error,{"error_code":"unsupported_format","offset":2070,
                                "message":"STEP node 39: Face has no boundary loops"})
        observations = corpus.load_json(case / "validation/observations.json")
        self.assertFalse(observations["library_step_produced"])

    def test_native_sphere_poles_periodicity_and_normals(self):
        native = corpus.load_json(ROOT / "cases/part-sphere-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":1,"edges":0,"vertices":0,"shells":1})
        self.assertLess(math.dist(body["measurements_si"]["centroid_m"],(0,0,0)),1e-12)
        entities = native["observations"]["brep"]["entities"]
        self.assertEqual([e["kind"] for e in entities],["body","shell","face","surface"])
        surface = entities[3]["geometry"]
        self.assertEqual(surface["type"],"sphere")
        self.assertEqual(surface["center"],[0,0,0])
        self.assertEqual(surface["radius"],.01)
        samples = native["observations"]["evaluations"]["evaluate-3"]["samples"]
        self.assertEqual(len(samples),25)
        for sample in samples:
            point = sample["position"]
            self.assertAlmostEqual(math.sqrt(sum(x*x for x in point)),.01,delta=1e-12)
            self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
            self.assertLess(math.dist(sample["face_normal"],[v/.01 for v in point]),1e-12)
        # Each U has the same physical poles, and U=0 and 2*pi coincide.
        for offset in (0,4):
            for block in range(1,5):
                self.assertLess(math.dist(samples[offset]["position"],samples[block*5+offset]["position"]),1e-12)
        self.assertAlmostEqual(math.dist(samples[0]["position"],samples[4]["position"]),.02,delta=1e-12)
        for offset in range(5):
            self.assertLess(math.dist(samples[offset]["position"],samples[20+offset]["position"]),1e-12)


class ExpectedExportFailureTest(unittest.TestCase):
    def setUp(self):
        import sys
        sys.path.insert(0,str(ROOT / "tools"))
        import run_case
        self.error_type = run_case.CorpusError
        self.verify = run_case.verify_export_failure
        self.expectation = {"outcome":"unsupported","error_code":"unsupported_format"}
        self.frozen = {"error_code":"unsupported_format","offset":2070,
                       "message":"STEP node 39: Face has no boundary loops"}

    def test_exact_failure_is_an_unsupported_match(self):
        self.verify(self.expectation,self.frozen,2,dict(self.frozen),False)

    def test_unexpected_success_partial_file_and_changed_diagnostics_fail(self):
        for mutation in ("success","partial-output","code","offset","message","missing-json"):
            actual = dict(self.frozen)
            if mutation in ("code","offset","message"):
                key = {"code":"error_code","offset":"offset","message":"message"}[mutation]
                actual[key] = 0 if mutation=="offset" else "changed"
            if mutation=="missing-json":
                actual = None
            with self.subTest(mutation=mutation), self.assertRaises(self.error_type):
                self.verify(self.expectation,self.frozen,0 if mutation=="success" else 2,
                            actual,mutation=="partial-output")


class CapturedSphereCapTest(unittest.TestCase):
    def test_admitted_cap_integrity(self):
        report = corpus.audit(ROOT,require_ready=True)
        self.assertIn("part-sphere-cap-001",{c["id"] for c in report["cases"]})

    def test_native_cap_circle_pole_and_material_normals(self):
        native = corpus.load_json(ROOT / "cases/part-sphere-cap-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":2,"edges":1,"vertices":0,"shells":1})
        self.assertLess(math.dist(body["measurements_si"]["centroid_m"],(0,0,.00675)),1e-12)
        count=surface_count=0
        entities = native["observations"]["brep"]["entities"]
        for label,evaluation in native["observations"]["evaluations"].items():
            entity = entities[int(label.split("-")[-1])]
            g = entity["geometry"]
            for sample in evaluation["samples"]:
                point = sample["position"]
                x,y,z = point
                self.assertGreaterEqual(z,.005-1e-12)
                self.assertLessEqual(z,.01+1e-12)
                self.assertLessEqual(math.sqrt(sum(v*v for v in point)),.01+1e-12)
                if entity["kind"]=="curve":
                    self.assertEqual(g["type"],"circle")
                    self.assertAlmostEqual(math.hypot(x,y),math.sqrt(75)*.001,delta=1e-12)
                    self.assertAlmostEqual(z,.005,delta=1e-12)
                else:
                    self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
                    if g["type"]=="sphere":
                        self.assertAlmostEqual(math.sqrt(sum(v*v for v in point)),.01,delta=1e-12)
                        expected = [v/.01 for v in point]
                        surface_count += 1
                    else:
                        self.assertEqual(g["type"],"plane")
                        self.assertAlmostEqual(z,.005,delta=1e-12)
                        expected = [0,0,-1]
                    self.assertLess(math.dist(sample["face_normal"],expected),1e-12)
                count += 1
        self.assertEqual((count,surface_count),(30,20))

    def test_oracle_projection_workaround_is_explicit_and_bounded(self):
        report = corpus.load_json(ROOT / "cases/part-sphere-cap-001/validation/occt.json")
        imported = report["native_reference_import"]
        self.assertTrue(imported["projection_rebuilt"])
        self.assertGreater(imported["raw_max_sampled_pcurve_error_mm"],.001)
        self.assertLessEqual(imported["repaired_max_sampled_pcurve_error_mm"],1e-5)
        self.assertLessEqual(imported["repaired_edge_tolerance_mm"],1e-5)
        self.assertEqual(report["bidirectional_difference_volume_mm3"],[0,0])
        seam = report["library_export"]["seams"][0]
        self.assertTrue(seam["exact_sphere_pcurve"])
        self.assertLessEqual(seam["radial_deviation_bound_mm"],seam["edge_tolerance_mm"])


class CapturedTorusTest(unittest.TestCase):
    def test_admitted_torus_has_exact_unsupported_export_expectation(self):
        corpus.audit(ROOT,require_ready=True)
        case = ROOT / "cases/part-torus-001"
        manifest = corpus.load_json(case / "case.json")
        self.assertEqual(manifest["expectations"]["step"]["outcome"],"unsupported")
        self.assertEqual(manifest["expectations"]["step"]["error_code"],"unsupported_format")
        self.assertEqual(corpus.load_json(case / "validation/export-error.json"),
                         {"error_code":"unsupported_format","offset":2078,
                          "message":"STEP node 39: Face has no boundary loops"})
        self.assertFalse(corpus.load_json(case / "validation/observations.json")["library_step_produced"])

    def test_native_torus_both_periods_and_inner_outer_material_normals(self):
        native = corpus.load_json(ROOT / "cases/part-torus-001/reference/native.json")
        body = native["bodies"][0]
        self.assertEqual(body["counts"],{"faces":1,"edges":0,"vertices":0,"shells":1})
        self.assertLess(math.dist(body["measurements_si"]["centroid_m"],(0,0,0)),1e-12)
        entities = native["observations"]["brep"]["entities"]
        self.assertEqual([e["kind"] for e in entities],["body","shell","face","surface"])
        g = entities[3]["geometry"]
        self.assertEqual(g["type"],"torus")
        self.assertTrue(g["u_periodic"] and g["v_periodic"] and g["u_closed"] and g["v_closed"])
        self.assertAlmostEqual(g["major_radius"],.02,delta=1e-12)
        self.assertAlmostEqual(g["minor_radius"],.005,delta=1e-12)
        samples = native["observations"]["evaluations"]["evaluate-3"]["samples"]
        self.assertEqual(len(samples),25)
        inner=outer=0
        for sample in samples:
            x,y,z = sample["position"]
            rho = math.hypot(x,y)
            self.assertAlmostEqual((rho-.02)**2+z*z,.005**2,delta=1e-15)
            self.assertTrue(sample["trim_membership"]["geometric_inside_or_boundary"])
            expected = [(rho-.02)*x/(.005*rho),(rho-.02)*y/(.005*rho),z/.005]
            self.assertLess(math.dist(sample["face_normal"],expected),1e-12)
            dot = x*sample["face_normal"][0]+y*sample["face_normal"][1]
            if abs(rho-.015)<1e-12:
                self.assertLess(dot,0)
                inner += 1
            if abs(rho-.025)<1e-12:
                self.assertGreater(dot,0)
                outer += 1
        self.assertGreater(inner,0)
        self.assertGreater(outer,0)
        for offset in range(5):
            self.assertLess(math.dist(samples[offset]["position"],samples[20+offset]["position"]),1e-12)
        for block in range(5):
            self.assertLess(math.dist(samples[5*block]["position"],samples[5*block+4]["position"]),1e-12)


if __name__ == "__main__":
    unittest.main()
