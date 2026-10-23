#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Check both captured/reference STEP cylinders in explicitly selected mm units."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SOLID
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def measure(shape, volume):
    if shape.IsNull():
        return 0.0
    properties = GProp_GProps()
    operation = BRepGProp.VolumeProperties_s if volume else BRepGProp.SurfaceProperties_s
    operation(shape, properties, Eps=1e-12)
    return properties.Mass()


def read_cylinder(path):
    reader = STEPControl_Reader()
    require(reader.ReadFile(str(path)) == IFSelect_RetDone, f"cannot read {path}")
    reader.SetSystemLengthUnit(1.0)  # One millimetre in OCCT's STEP unit convention.
    require(reader.TransferRoots() == 1, "expected exactly one STEP root")
    shape = reader.OneShape()
    require(not shape.IsNull() and BRepCheck_Analyzer(shape).IsValid(), "invalid B-rep")
    counts = {}
    for name, kind in (("faces", TopAbs_FACE), ("edges", TopAbs_EDGE),
                       ("vertices", TopAbs_VERTEX), ("solids", TopAbs_SOLID)):
        entities = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, kind, entities)
        counts[name] = entities.Extent()
    require(counts["faces"] == 3 and counts["solids"] == 1, "incomplete cylinder")
    faces = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    cylinders, plane_z = 0, []
    for index in range(1, faces.Extent()+1):
        surface = BRepAdaptor_Surface(TopoDS.Face_s(faces.FindKey(index)))
        if surface.GetType() == GeomAbs_Cylinder:
            cylinders += 1
            cylinder = surface.Cylinder()
            require(abs(cylinder.Radius()-10) < 1e-8, "wrong cylinder radius")
            axis = cylinder.Axis()
            require(abs(abs(axis.Direction().Z())-1) < 1e-12, "wrong cylinder axis")
            require(math.hypot(axis.Location().X(), axis.Location().Y()) < 1e-8,
                    "wrong cylinder placement")
        else:
            require(surface.GetType() == GeomAbs_Plane, "unexpected support surface")
            plane = surface.Plane()
            require(abs(abs(plane.Axis().Direction().Z())-1) < 1e-12,
                    "wrong cap orientation")
            plane_z.append(plane.Location().Z())
    require(cylinders == 1 and len(plane_z) == 2, "wrong support surface inventory")
    require(all(abs(a-b) < 1e-8 for a,b in zip(sorted(plane_z), (0,20))),
            "wrong cylinder height or cap placement")
    volume, area = measure(shape, True), measure(shape, False)
    require(math.isclose(volume, math.pi*10**2*20, rel_tol=1e-9), "wrong volume")
    require(math.isclose(area, 2*math.pi*10*(10+20), rel_tol=1e-9), "wrong area")
    return shape, {"topology": counts, "volume_mm3": volume, "area_mm2": area,
                   "cap_z_mm": sorted(plane_z), "brep_valid": True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_cylinder_step.py <native.step> <exported.step>")
    native, native_report = read_cylinder(Path(sys.argv[1]))
    exported, exported_report = read_cylinder(Path(sys.argv[2]))
    differences = []
    for first, second in ((native, exported), (exported, native)):
        cut = BRepAlgoAPI_Cut(first, second)
        require(cut.IsDone(), "geometric difference operation failed")
        remainder = abs(measure(cut.Shape(), True))
        require(remainder < 1e-6, "solid difference exceeds 1e-6 mm^3")
        differences.append(remainder)
    print(json.dumps({"ocp_distribution_version": importlib.metadata.version("cadquery-ocp"),
                      "native_reference": native_report, "library_export": exported_report,
                      "bidirectional_difference_volume_mm3": differences}, indent=2))


if __name__ == "__main__":
    main()
