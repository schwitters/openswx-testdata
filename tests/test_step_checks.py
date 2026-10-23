# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Optional OCCT checks that distinguish equal measures from equal geometry."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
try:
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf, gp_Vec
    from check_block_step import check_block_shape
    from check_tube_step import check_tube_shape
    from step_check import measure
    HAS_OCCT = True
except ModuleNotFoundError as error:
    if error.name != "OCP" and not error.name.startswith("OCP."):
        raise
    HAS_OCCT = False


@unittest.skipUnless(HAS_OCCT, "install requirements-occt.txt for kernel checks")
class BlockGeometryTest(unittest.TestCase):
    def test_expected_block(self):
        report = check_block_shape(BRepPrimAPI_MakeBox(20,30,40).Shape())
        self.assertAlmostEqual(report["volume_mm3"], 24000, delta=1e-6)

    def test_translation_with_identical_measures_is_rejected(self):
        transform = gp_Trsf()
        transform.SetTranslation(gp_Vec(1,0,0))
        moved = BRepPrimAPI_MakeBox(20,30,40).Shape().Moved(TopLoc_Location(transform))
        with self.assertRaisesRegex(RuntimeError, "dimension or placement"):
            check_block_shape(moved)

    def test_swapped_dimensions_with_identical_measures_are_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "dimension or placement"):
            check_block_shape(BRepPrimAPI_MakeBox(30,20,40).Shape())


@unittest.skipUnless(HAS_OCCT, "install requirements-occt.txt for kernel checks")
class TubeGeometryTest(unittest.TestCase):
    @staticmethod
    def make_tube(eccentricity=0):
        outer = BRepPrimAPI_MakeCylinder(10,20).Shape()
        inner = BRepPrimAPI_MakeCylinder(5,20).Shape()
        if eccentricity:
            transform = gp_Trsf()
            transform.SetTranslation(gp_Vec(eccentricity,0,0))
            inner = inner.Moved(TopLoc_Location(transform))
        cut = BRepAlgoAPI_Cut(outer,inner)
        if not cut.IsDone():
            raise RuntimeError("Test tube construction failed")
        return cut.Shape()

    def test_expected_tube(self):
        report = check_tube_shape(self.make_tube())
        self.assertEqual(report["cylinder_radii_mm"], [5,10])
        self.assertEqual(report["annular_cap_wire_counts"], [2,2])

    def test_eccentric_bore_with_identical_measures_is_rejected(self):
        reference, eccentric = self.make_tube(), self.make_tube(1)
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume), measure(eccentric,volume), delta=1e-6)
        with self.assertRaisesRegex(RuntimeError, "placement or eccentric bore"):
            check_tube_shape(eccentric)

    def test_translated_tube_is_rejected(self):
        transform = gp_Trsf()
        transform.SetTranslation(gp_Vec(0,0,1))
        moved = self.make_tube().Moved(TopLoc_Location(transform))
        with self.assertRaisesRegex(RuntimeError, "height or cap placement"):
            check_tube_shape(moved)

    def test_filled_bore_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete tube"):
            check_tube_shape(BRepPrimAPI_MakeCylinder(10,20).Shape())


if __name__ == "__main__":
    unittest.main()
