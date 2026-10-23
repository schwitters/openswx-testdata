#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Check an R3 through bore with an R6 x depth8 counterbore in R10 x H20 stock."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import (axial_seam_data, compare_solids, measure, read_step,
                        require, topology_counts)


def check_stepped_bore_shape(shape):
    counts = topology_counts(shape)
    require(counts["faces"] == 6 and counts["solids"] == 1, "incomplete stepped-bore solid")
    faces, edges = TopTools_IndexedMapOfShape(), TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    cylinders, radii, planes = [], [], []
    for index in range(1, faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index))
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinders.append(face)
            cylinder = surface.Cylinder()
            radii.append(cylinder.Radius())
            axis = cylinder.Axis()
            require(abs(abs(axis.Direction().Z())-1) < 1e-12, "wrong bore axis")
            require(math.hypot(axis.Location().X(), axis.Location().Y()) < 1e-8,
                    "eccentric bore or shifted solid")
        else:
            require(surface.GetType() == GeomAbs_Plane, "unexpected stepped-bore surface")
            plane = surface.Plane()
            require(abs(abs(plane.Axis().Direction().Z())-1) < 1e-12, "oblique cap or shoulder")
            wires = TopExp_Explorer(face, TopAbs_WIRE)
            wire_count = 0
            while wires.More():
                wire_count += 1
                wires.Next()
            planes.append((plane.Location().Z(), wire_count))
    require(len(radii) == 3 and all(abs(a-b) < 1e-8 for a,b in zip(sorted(radii),(3,6,10))),
            "wrong bore or stock radius")
    expected_planes = ((0,2),(12,2),(20,2))
    require(len(planes) == 3 and all(abs(a[0]-b[0]) < 1e-8 and a[1] == b[1]
            for a,b in zip(sorted(planes), expected_planes)), "wrong counterbore entry or shoulder")
    rings, seams = [], []
    for index in range(1, edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(index))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType() == GeomAbs_Circle:
            circle = curve.Circle()
            require(math.hypot(circle.Location().X(), circle.Location().Y()) < 1e-8 and
                    abs(abs(circle.Axis().Direction().Z())-1) < 1e-12,
                    "shifted or tilted ring")
            require(abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi) < 1e-12,
                    "incomplete ring")
            rings.append((circle.Radius(), circle.Location().Z()))
        else:
            seams.append(axial_seam_data(edge, curve, cylinders))
    expected_rings = ((3,0),(3,12),(6,12),(6,20),(10,0),(10,20))
    require(len(rings) == 6 and all(math.dist(a,b) < 1e-8 for a,b in
            zip(sorted(rings), expected_rings)), "wrong bore depth or ring geometry")
    seams.sort(key=lambda item: item["radius_mm"])
    require(len(seams) == 3 and all(math.dist(
            (seam["radius_mm"], *seam["z_span_mm"]), expected) < 1e-8
            for seam,expected in zip(seams, ((3,0,12),(6,12,20),(10,0,20)))), "wrong cylinder seam span")
    volume, area = measure(shape, True), measure(shape, False)
    require(math.isclose(volume, 1604*math.pi, rel_tol=1e-9), "wrong stepped-bore volume")
    require(math.isclose(area, 750*math.pi, rel_tol=1e-9), "wrong stepped-bore area")
    return {"topology": counts, "volume_mm3": volume, "area_mm2": area,
            "plane_z_and_wire_count": sorted(planes), "ring_radius_and_z_mm": sorted(rings),
            "seams": seams, "brep_valid": True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_stepped_bore_step.py <native.step> <exported.step>")
    native, _ = read_step(Path(sys.argv[1]))
    exported, _ = read_step(Path(sys.argv[2]))
    native_report = check_stepped_bore_shape(native)
    exported_report = check_stepped_bore_shape(exported)
    print(json.dumps({"ocp_distribution_version": importlib.metadata.version("cadquery-ocp"),
                      "native_reference": native_report, "library_export": exported_report,
                      "bidirectional_difference_volume_mm3": compare_solids(native,exported)}, indent=2))


if __name__ == "__main__":
    main()
