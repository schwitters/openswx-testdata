# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Temporary dummy bytes test contracts; they are not CAD fixtures."""
import hashlib
import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
