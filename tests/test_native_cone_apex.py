# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Frozen native isolated-apex regression and independent geometric negatives."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "verification/cone-apex-001"
sys.path.insert(0, str(ROOT / "tools"))
from verify_cone_apex import apex_pattern, audit, step_cone_bound, verify

try:
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeCone, BRepPrimAPI_MakeCylinder
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
    from check_cone_apex_step import check_shape
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


class NativeConeApexEvidenceTest(unittest.TestCase):
    def test_original_artifacts_and_export_receipts_are_hash_verified(self):
        expected = audit(DATA)
        manifest = json.loads((DATA / "manifest.json").read_text())
        self.assertEqual(manifest["origin"], "original_synthetic")
        self.assertEqual(manifest["license"], "MIT")
        self.assertEqual({c["name"] for c in expected["cases"]}, {"cone", "blind-drill"})
        receipts = json.loads((DATA / "receipts.json").read_text())
        for case in expected["cases"]:
            for key, filename in (("source", case["source"]), ("step", case["step"])):
                data = (DATA / filename).read_bytes()
                receipt = receipts[case["name"]][key]
                self.assertEqual(len(data), receipt["byte_length"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), receipt["sha256"])

    def test_reopened_native_models_reproduce_the_source_loop_pattern(self):
        expected = audit(DATA)
        source = json.loads((DATA / "source-inspection.json").read_text())
        for case in expected["cases"]:
            captured = source[case["name"]]
            self.assertTrue(captured["topology"]["complete"])
            self.assertTrue(captured["geometry"]["complete"])
            pattern = apex_pattern(captured["topology"]["body_topology"], captured["geometry"]["model"])
            self.assertEqual(pattern, case["apex_pattern"])
            self.assertEqual(pattern["loop_count"], 2)
            self.assertEqual(pattern["isolated_loop_count"], 1)
            self.assertEqual(step_cone_bound(DATA / case["step"])["bounds"], 1)
            props = case["native_measurement"]["mass_properties"]
            if case["name"] == "cone":
                volume = 120 * math.pi * 1e-9
                area = math.pi * (36 + 6 * math.sqrt(136)) * 1e-6
            else:
                volume = math.pi * (6750 - 160 - 40 / 3) * 1e-9
                area = math.pi * (900 + 225 + 209 + 80 + 4 * math.sqrt(22.25)) * 1e-6
            self.assertTrue(math.isclose(props["volume"], volume, rel_tol=1e-9))
            self.assertTrue(math.isclose(props["area"], area, rel_tol=1e-9))
            native = case["native_measurement"]["topology_counts"]
            self.assertEqual(native["bodies"], 1)
            self.assertEqual(native["vertices"], 1)
            self.assertEqual(native["faces"], 2 if case["name"] == "cone" else 5)
            self.assertAlmostEqual(pattern["apex_position_m"][2], .01 if case["name"] == "cone" else .0175)

    def test_pre_fix_control_fails_without_writing_a_partial_document(self):
        controls = json.loads((DATA / "regression-control.json").read_text())
        self.assertEqual(controls["before_body_writer_commit"], "b419a94")
        for name in ("cone", "blind-drill"):
            before = next(r for r in controls["results"] if r["fixture"] == name and r["control"] == "before")
            after = next(r for r in controls["results"] if r["fixture"] == name and r["control"] == "after")
            self.assertEqual(before["exit_code"], 2)
            self.assertFalse(before["output_exists"])
            self.assertEqual(before["stdout"]["error_code"], "unsupported_format")
            self.assertIn("Ruled patches require one non-isolated loop", before["stdout"]["message"])
            self.assertEqual(after["exit_code"], 0)
            self.assertEqual(after["stdout"]["solids"], 1)

    def test_native_construction_and_reopen_are_recorded_without_imported_geometry(self):
        capture = json.loads((DATA / "capture.json").read_text())
        self.assertTrue(capture["documents_closed"])
        self.assertFalse(capture["authentication_headers_recorded"])
        events = {e["label"]: e for e in capture["events"]}
        for name in ("cone", "blind-drill"):
            self.assertEqual(events[name + "-new"]["request"]["params"]["name"], "sw.document.new")
            self.assertEqual(events[name + "-reopen"]["request"]["params"]["name"], "sw.document.open")
            opened = events[name + "-reopen"]["request"]["params"]["arguments"]["path"]
            self.assertIn("openswx-tests", opened)
            self.assertTrue(opened.endswith(name + ".sldprt"))
            feature = events[name + "-revolve"]["request"]["params"]["arguments"]["params"]["feature"]
            self.assertEqual(feature["type"], "revolve")
            self.assertEqual(feature["operation"], "new_body" if name == "cone" else "cut")
            self.assertAlmostEqual(feature["angle"], 2 * math.pi)
            if name == "blind-drill":
                self.assertEqual(len(feature["targets"]), 1)
            for scope in ("document", "configuration"):
                response = events[name + "-properties-" + scope]["response"]["result"]["structuredContent"]["result"]
                self.assertEqual(response["properties"], [])


@unittest.skipUnless(HAVE_OCP, "optional cadquery-ocp is not installed")
class ConeApexGeometryTest(unittest.TestCase):
    @staticmethod
    def drill():
        blank = BRepPrimAPI_MakeCylinder(15, 30).Shape()
        bore = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 20), gp_Dir(0, 0, 1)), 4, 10).Shape()
        tip = BRepPrimAPI_MakeCone(gp_Ax2(gp_Pnt(0, 0, 17.5), gp_Dir(0, 0, 1)), 0, 4, 2.5).Shape()
        return BRepAlgoAPI_Cut(BRepAlgoAPI_Cut(blank, bore).Shape(), tip).Shape()

    def test_independent_kernel_constructed_cone_and_drill(self):
        self.assertTrue(check_shape(BRepPrimAPI_MakeCone(6, 0, 10).Shape(), "cone")["brep_valid"])
        self.assertTrue(check_shape(self.drill(), "blind-drill")["cone_material_normals_verified"])

    def test_equal_measure_reverse_taper_is_rejected(self):
        with self.assertRaises(RuntimeError):
            check_shape(BRepPrimAPI_MakeCone(0, 6, 10).Shape(), "cone")

    def test_translated_geometry_and_inverted_material_are_rejected(self):
        cone = BRepPrimAPI_MakeCone(6, 0, 10).Shape()
        shift = gp_Trsf()
        shift.SetTranslation(gp_Vec(1, 0, 0))
        with self.assertRaises(RuntimeError):
            check_shape(cone.Moved(TopLoc_Location(shift)), "cone")
        with self.assertRaises(RuntimeError):
            check_shape(cone.Reversed(), "cone")
        with self.assertRaises(RuntimeError):
            check_shape(self.drill().Reversed(), "blind-drill")

    def test_flat_bottom_bore_does_not_substitute_for_a_conical_tip(self):
        blank = BRepPrimAPI_MakeCylinder(15, 30).Shape()
        bore = BRepPrimAPI_MakeCylinder(gp_Ax2(gp_Pnt(0, 0, 20), gp_Dir(0, 0, 1)), 4, 10).Shape()
        with self.assertRaises(RuntimeError):
            check_shape(BRepAlgoAPI_Cut(blank, bore).Shape(), "blind-drill")


@unittest.skipUnless(all(os.environ.get("OPENSWX_CORPUS_" + name)
                         for name in ("BUILD", "EXPORTER", "OCCT_PYTHON")),
                     "set OPENSWX_CORPUS_BUILD, EXPORTER and OCCT_PYTHON for native integration")
class ConeApexLibraryIntegrationTest(unittest.TestCase):
    def test_all_three_libraries_against_native_references(self):
        with tempfile.TemporaryDirectory(prefix="cone-apex-test-") as tmp:
            baseline = os.environ.get("OPENSWX_CORPUS_BASELINE_EXPORTER")
            report = verify(DATA, Path(os.environ["OPENSWX_CORPUS_BUILD"]).resolve(),
                            Path(os.environ["OPENSWX_CORPUS_EXPORTER"]).resolve(),
                            Path(os.environ["OPENSWX_CORPUS_OCCT_PYTHON"]).absolute(),
                            Path(tmp) / "regression", Path(baseline).resolve() if baseline else None)
            self.assertEqual(len(report["cases"]), 2)
            for case in report["cases"]:
                self.assertEqual(set(case["stages"].values()), {"pass"})
                if baseline:
                    self.assertTrue(case["baseline_failure_reproduced"])
