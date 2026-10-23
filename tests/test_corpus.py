# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Admission contracts and native observations; dummy bytes stay temporary."""
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


if __name__ == "__main__":
    unittest.main()
