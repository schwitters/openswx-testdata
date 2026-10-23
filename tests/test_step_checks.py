# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Optional OCCT checks that distinguish equal measures from equal geometry."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
try:
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.TopLoc import TopLoc_Location
    from OCP.gp import gp_Trsf, gp_Vec
    from check_block_step import check_block_shape
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


if __name__ == "__main__":
    unittest.main()
