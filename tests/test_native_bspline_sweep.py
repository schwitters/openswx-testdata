# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Original native B-spline sweep fixtures and their current explicit limit."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "verification/bspline-sweep-001"
sys.path.insert(0, str(ROOT / "tools"))
from verify_bspline_sweep import MESSAGE, audit, swept_pattern, verify

try:
    from OCP.BRepAdaptor import BRepAdaptor_Curve
    from OCP.GeomAbs import GeomAbs_BSplineCurve
    from OCP.TopAbs import TopAbs_EDGE
    from OCP.TopExp import TopExp
    from OCP.TopTools import TopTools_IndexedMapOfShape
    from OCP.TopoDS import TopoDS
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf, gp_Vec
    from check_bspline_sweep_step import analytic, check_shape
    from step_check import read_step
    HAVE_OCP = True
except ModuleNotFoundError:
    HAVE_OCP = False


class NativeBSplineSweepEvidenceTest(unittest.TestCase):
    def test_original_artifacts_match_native_receipts(self):
        expected = audit(DATA)
        receipts = json.loads((DATA / "receipts.json").read_text())
        for case in expected["cases"]:
            for role, field in (("source", "source"), ("step", "step")):
                data = (DATA / case[field]).read_bytes()
                receipt = receipts[case["name"]][role]
                self.assertEqual(len(data), receipt["byte_length"])
                self.assertEqual(hashlib.sha256(data).hexdigest(), receipt["sha256"])

    def test_typed_cubic_sections_are_not_missing_or_misdecoded_geometry(self):
        source = json.loads((DATA / "source-inspection.json").read_text())
        expected = audit(DATA)
        for case in expected["cases"]:
            captured = source[case["name"]]
            self.assertTrue(captured["topology"]["complete"])
            self.assertTrue(captured["geometry"]["complete"])
            model = captured["geometry"]["model"]
            self.assertTrue(model["typed_geometry_complete"])
            self.assertEqual(model["issue_count"], 0)
            pattern = swept_pattern(captured["topology"]["body_topology"], model)
            self.assertEqual(pattern, case["swept_pattern"])
            self.assertEqual(pattern["degree"], 3)
            self.assertEqual(pattern["control_count"], 4 if case["name"] == "cubic" else 6)
            self.assertEqual(len(pattern["knots"]), 2 if case["name"] == "cubic" else 4)
            self.assertEqual(case["source_topology"], {"faces": 5, "edges": 9, "vertices": 6})
            self.assertEqual(captured["binding_error"]["code"], "unsupported_format")
            self.assertIn(MESSAGE, captured["binding_error"]["message"])

    def test_current_export_failure_publishes_no_partial_step(self):
        errors = json.loads((DATA / "export-errors.json").read_text())
        self.assertEqual({c["name"] for c in errors["cases"]}, {"cubic", "multispan"})
        for case in errors["cases"]:
            self.assertEqual(case["exit_code"], 2)
            self.assertFalse(case["partial_output_created"])
            self.assertEqual(case["error"]["error_code"], "unsupported_format")
            self.assertIn(MESSAGE, case["error"]["message"])

    def test_native_construction_and_empty_properties_are_recorded(self):
        recipe = json.loads((DATA / "recipe.json").read_text())
        self.assertEqual(recipe["origin"], "original_synthetic")
        self.assertEqual(recipe["license"], "MIT")
        capture = json.loads((DATA / "capture.json").read_text())
        self.assertTrue(capture["documents_closed"])
        self.assertFalse(capture["authentication_headers_recorded"])
        events = {e["label"]: e for e in capture["events"]}
        for case in recipe["cases"]:
            name = case["name"]
            self.assertEqual(events[name + "-new"]["request"]["params"]["name"], "sw.document.new")
            entities = events[name + "-sketch"]["request"]["params"]["arguments"]["params"]["sketch"]["entities"]
            self.assertEqual(entities[0]["type"], "bspline")
            self.assertEqual(entities[0]["control_points"], case["controls_m"])
            self.assertEqual(entities[0]["knots"], case["knots"])
            for scope in ("document", "configuration"):
                response = events[name + "-properties-" + scope]["response"]["result"]["structuredContent"]["result"]
                self.assertEqual(response["properties"], [])

    def test_native_default_mass_cache_is_distinct_from_geometric_oracle(self):
        oracle = json.loads((DATA / "occt.json").read_text())
        self.assertAlmostEqual(oracle["cubic"]["analytic"]["volume_mm3"], 648)
        self.assertAlmostEqual(oracle["multispan"]["analytic"]["volume_mm3"], 545.013225)
        for result in oracle.values():
            self.assertTrue(result["native_default_mass_properties_are_approximate"])
            self.assertGreater(result["native_volume_relative_error_vs_analytic"], 1e-9)
            self.assertTrue(math.isclose(result["volume_mm3"], result["analytic"]["volume_mm3"], rel_tol=1e-12))


@unittest.skipUnless(HAVE_OCP, "optional cadquery-ocp is not installed")
class BSplineSweepGeometryTest(unittest.TestCase):
    def test_native_solids_match_independent_piecewise_polynomials(self):
        for name in ("cubic", "multispan"):
            shape, _ = read_step(DATA / (name + ".step"))
            checked = check_shape(shape, name)
            self.assertTrue(checked["cubic_profile_and_material_normals_verified"])
            self.assertTrue(math.isclose(checked["volume_mm3"], analytic(name)["volume_mm3"], rel_tol=1e-12))

    def test_equal_volume_translation_and_reversed_material_are_rejected(self):
        for name in ("cubic", "multispan"):
            shape, _ = read_step(DATA / (name + ".step"))
            shift = gp_Trsf()
            shift.SetTranslation(gp_Vec(1, 0, 0))
            with self.assertRaises(RuntimeError):
                check_shape(shape.Moved(TopLoc_Location(shift)), name)
            with self.assertRaises(RuntimeError):
                check_shape(shape.Reversed(), name)

    def test_nonuniform_profile_has_genuine_piecewise_cubic_terms(self):
        shape, _ = read_step(DATA / "multispan.step")
        edges = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
        profiles = 0
        for i in range(1, edges.Extent() + 1):
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
            if curve.GetType() != GeomAbs_BSplineCurve:
                continue
            point = curve.Value((curve.FirstParameter() + curve.LastParameter()) / 2)
            u = (point.Y() + 10) / 12
            self.assertGreater(abs(point.Z() - 5 - 9 * u ** 3), 1e-3)
            profiles += 1
        self.assertEqual(profiles, 2)


@unittest.skipUnless(all(os.environ.get("OPENSWX_CORPUS_" + name)
                         for name in ("BUILD", "EXPORTER", "OCCT_PYTHON")),
                     "set OPENSWX_CORPUS_BUILD, EXPORTER and OCCT_PYTHON for native integration")
class BSplineSweepLibraryIntegrationTest(unittest.TestCase):
    def test_exact_binding_limit_and_no_partial_export(self):
        with tempfile.TemporaryDirectory(prefix="bspline-sweep-test-") as tmp:
            report = verify(DATA, Path(os.environ["OPENSWX_CORPUS_BUILD"]).resolve(),
                            Path(os.environ["OPENSWX_CORPUS_EXPORTER"]).resolve(),
                            Path(os.environ["OPENSWX_CORPUS_OCCT_PYTHON"]).absolute(), Path(tmp) / "verification")
            self.assertEqual(len(report["cases"]), 2)
            for case in report["cases"]:
                self.assertEqual(case["stages"]["topology"], "pass")
                self.assertEqual(case["stages"]["binding"], "expected_unsupported")
                self.assertEqual(case["stages"]["step"], "expected_unsupported")
                self.assertFalse(case["partial_output_created"])
