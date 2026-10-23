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
    from check_blind_hole_step import check_blind_hole_shape
    from check_through_hole_step import check_through_hole_shape
    from check_stepped_bore_step import check_stepped_bore_shape
    from check_two_holes_step import check_two_holes_shape
    from OCP.GProp import GProp_GProps
    from OCP.BRepGProp import BRepGProp
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


@unittest.skipUnless(HAS_OCCT, "install requirements-occt.txt for kernel checks")
class BlindHoleGeometryTest(unittest.TestCase):
    @staticmethod
    def make_blind_hole(top_entry=True, depth=10, eccentricity=0):
        stock = BRepPrimAPI_MakeCylinder(10,20).Shape()
        bore = BRepPrimAPI_MakeCylinder(5,depth).Shape()
        transform = gp_Trsf()
        transform.SetTranslation(gp_Vec(eccentricity,0,20-depth if top_entry else 0))
        bore = bore.Moved(TopLoc_Location(transform))
        cut = BRepAlgoAPI_Cut(stock,bore)
        if not cut.IsDone():
            raise RuntimeError("Test blind-hole construction failed")
        return cut.Shape()

    def test_expected_blind_hole(self):
        report = check_blind_hole_shape(self.make_blind_hole())
        self.assertEqual(report["plane_z_and_wire_count"], [(0,1),(10,1),(20,2)])

    def test_wrong_entry_with_identical_measures_is_rejected(self):
        reference, reversed_entry = self.make_blind_hole(), self.make_blind_hole(False)
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume), measure(reversed_entry,volume), delta=1e-6)
        with self.assertRaisesRegex(RuntimeError, "entry or floor"):
            check_blind_hole_shape(reversed_entry)

    def test_wrong_depth_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "entry or floor"):
            check_blind_hole_shape(self.make_blind_hole(depth=8))

    def test_through_hole_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "incomplete blind-hole"):
            check_blind_hole_shape(self.make_blind_hole(depth=20))

    def test_eccentric_blind_hole_is_rejected(self):
        reference, eccentric = self.make_blind_hole(), self.make_blind_hole(eccentricity=1)
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume), measure(eccentric,volume), delta=1e-6)
        with self.assertRaisesRegex(RuntimeError, "eccentric bore"):
            check_blind_hole_shape(eccentric)


@unittest.skipUnless(HAS_OCCT, "install requirements-occt.txt for kernel checks")
class ThroughHoleGeometryTest(unittest.TestCase):
    @staticmethod
    def make_through_hole(x=10,y=15,depth=40):
        stock = BRepPrimAPI_MakeBox(20,30,40).Shape()
        bore = BRepPrimAPI_MakeCylinder(5,depth).Shape()
        transform = gp_Trsf()
        transform.SetTranslation(gp_Vec(x,y,40-depth))
        cut = BRepAlgoAPI_Cut(stock,bore.Moved(TopLoc_Location(transform)))
        if not cut.IsDone():
            raise RuntimeError("Test through-hole construction failed")
        return cut.Shape()

    def test_expected_through_hole(self):
        report = check_through_hole_shape(self.make_through_hole())
        self.assertEqual(report["ring_z_mm"],[0,40])
        self.assertEqual(report["bore_center_xy_mm"],[10,15])

    def test_shifted_bore_with_identical_measures_is_rejected(self):
        reference,shifted = self.make_through_hole(),self.make_through_hole(x=11)
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume),measure(shifted,volume),delta=1e-6)
        with self.assertRaisesRegex(RuntimeError,"bore position"):
            check_through_hole_shape(shifted)

    def test_blind_bore_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"incomplete through-hole"):
            check_through_hole_shape(self.make_through_hole(depth=20))

    def test_missing_bore_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"incomplete through-hole"):
            check_through_hole_shape(BRepPrimAPI_MakeBox(20,30,40).Shape())


@unittest.skipUnless(HAS_OCCT,"install requirements-occt.txt for kernel checks")
class SteppedBoreGeometryTest(unittest.TestCase):
    @staticmethod
    def make_stepped_bore(top_entry=True,depth=8,eccentricity=0):
        stock = BRepPrimAPI_MakeCylinder(10,20).Shape()
        bore = BRepPrimAPI_MakeCylinder(3,20).Shape()
        cut = BRepAlgoAPI_Cut(stock,bore)
        if not cut.IsDone():
            raise RuntimeError("Test through bore failed")
        counterbore = BRepPrimAPI_MakeCylinder(6,depth).Shape()
        transform = gp_Trsf()
        transform.SetTranslation(gp_Vec(eccentricity,0,20-depth if top_entry else 0))
        cut = BRepAlgoAPI_Cut(cut.Shape(),counterbore.Moved(TopLoc_Location(transform)))
        if not cut.IsDone():
            raise RuntimeError("Test counterbore failed")
        return cut.Shape()

    def test_expected_stepped_bore(self):
        report = check_stepped_bore_shape(self.make_stepped_bore())
        self.assertEqual(report["plane_z_and_wire_count"],[(0,2),(12,2),(20,2)])

    def test_reversed_entry_with_identical_measures_is_rejected(self):
        reference,reversed_entry = self.make_stepped_bore(),self.make_stepped_bore(False)
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume),measure(reversed_entry,volume),delta=1e-6)
        with self.assertRaisesRegex(RuntimeError,"entry or shoulder"):
            check_stepped_bore_shape(reversed_entry)

    def test_wrong_depth_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"entry or shoulder"):
            check_stepped_bore_shape(self.make_stepped_bore(depth=6))

    def test_missing_shoulder_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"incomplete stepped-bore"):
            check_stepped_bore_shape(self.make_stepped_bore(depth=20))

    def test_eccentric_counterbore_with_identical_measures_is_rejected(self):
        reference,eccentric = self.make_stepped_bore(),self.make_stepped_bore(eccentricity=1)
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume),measure(eccentric,volume),delta=1e-6)
        with self.assertRaisesRegex(RuntimeError,"eccentric bore"):
            check_stepped_bore_shape(eccentric)


@unittest.skipUnless(HAS_OCCT,"install requirements-occt.txt for kernel checks")
class TwoHolesGeometryTest(unittest.TestCase):
    @staticmethod
    def make_two_holes(centers=((10,15),(30,15)),second_depth=20):
        shape = BRepPrimAPI_MakeBox(40,30,20).Shape()
        for index,(x,y) in enumerate(centers):
            depth = second_depth if index == 1 else 20
            bore = BRepPrimAPI_MakeCylinder(3,depth).Shape()
            transform = gp_Trsf()
            transform.SetTranslation(gp_Vec(x,y,20-depth))
            cut = BRepAlgoAPI_Cut(shape,bore.Moved(TopLoc_Location(transform)))
            if not cut.IsDone():
                raise RuntimeError("Test repeated bore construction failed")
            shape = cut.Shape()
        return shape

    def test_expected_two_holes(self):
        report = check_two_holes_shape(self.make_two_holes())
        self.assertEqual([b["center_xy_mm"] for b in report["bores"]],[(10,15),(30,15)])

    def test_reversed_construction_order_preserves_geometric_ownership(self):
        report = check_two_holes_shape(self.make_two_holes(centers=((30,15),(10,15))))
        self.assertEqual([b["center_xy_mm"] for b in report["bores"]],[(10,15),(30,15)])

    def test_symmetric_shift_with_identical_measures_and_centroid_is_rejected(self):
        reference,shifted = self.make_two_holes(),self.make_two_holes(centers=((11,15),(29,15)))
        for volume in (True,False):
            self.assertAlmostEqual(measure(reference,volume),measure(shifted,volume),delta=1e-6)
        centroids = []
        for shape in (reference,shifted):
            properties = GProp_GProps()
            BRepGProp.VolumeProperties_s(shape,properties)
            center = properties.CentreOfMass()
            centroids.append((center.X(),center.Y(),center.Z()))
        self.assertLess(sum((a-b)**2 for a,b in zip(*centroids))**.5,1e-8)
        with self.assertRaisesRegex(RuntimeError,"bore position"):
            check_two_holes_shape(shifted)

    def test_one_missing_bore_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"incomplete two-hole"):
            check_two_holes_shape(self.make_two_holes(centers=((10,15),)))

    def test_one_blind_bore_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"incomplete two-hole"):
            check_two_holes_shape(self.make_two_holes(second_depth=10))


if __name__ == "__main__":
    unittest.main()
