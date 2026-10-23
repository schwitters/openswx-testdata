#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify the concentric R10/r5, 20 mm tube and its annular caps."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import (GeomAbs_BSplineCurve, GeomAbs_Circle, GeomAbs_Cylinder,
                         GeomAbs_Line, GeomAbs_Plane)
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import compare_solids, measure, read_step, require, topology_counts


def check_tube_shape(shape):
    counts = topology_counts(shape)
    require(counts["faces"] == 4 and counts["solids"] == 1, "incomplete tube")
    faces, edges = TopTools_IndexedMapOfShape(), TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    radii, caps, cylindrical_faces = [], [], []
    for index in range(1, faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index))
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Cylinder:
            cylindrical_faces.append(face)
            cylinder = surface.Cylinder()
            radii.append(cylinder.Radius())
            axis = cylinder.Axis()
            require(abs(abs(axis.Direction().Z())-1) < 1e-12, "wrong tube axis")
            require(math.hypot(axis.Location().X(), axis.Location().Y()) < 1e-8,
                    "wrong tube placement or eccentric bore")
        else:
            require(surface.GetType() == GeomAbs_Plane, "unexpected tube surface")
            plane = surface.Plane()
            require(abs(abs(plane.Axis().Direction().Z())-1) < 1e-12, "oblique tube cap")
            caps.append(plane.Location().Z())
            wires = TopExp_Explorer(face, TopAbs_WIRE)
            wire_count = 0
            while wires.More():
                wire_count += 1
                wires.Next()
            require(wire_count == 2, "tube cap must preserve its inner hole")
    require(len(radii) == 2 and all(abs(a-b) < 1e-8 for a,b in zip(sorted(radii), (5,10))),
            "wrong inner or outer tube radius")
    require(len(caps) == 2 and all(abs(a-b) < 1e-8 for a,b in zip(sorted(caps), (0,20))),
            "wrong tube height or cap placement")
    circle_radii, seam_radii, seam_representations = [], [], []
    for index in range(1, edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(index))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType() == GeomAbs_Circle:
            circle_radii.append(curve.Circle().Radius())
        else:
            # OCCT adds periodic seams absent from both original STEP files.
            # Some are exact two-pole, degree-one polynomial B-splines.
            require(any(BRep_Tool.IsClosed_s(edge, face) for face in cylindrical_faces),
                    "extra edge is not a periodic cylinder seam")
            if curve.GetType() == GeomAbs_BSplineCurve:
                spline = curve.BSpline()
                require(spline.Degree() == 1 and spline.NbPoles() == 2 and
                        not spline.IsRational(), "uncertified spline seam")
                seam_representations.append("polynomial_degree_1_bspline")
            else:
                require(curve.GetType() == GeomAbs_Line, "unexpected tube seam basis")
                seam_representations.append("line")
            first, last = curve.Value(curve.FirstParameter()), curve.Value(curve.LastParameter())
            require(math.hypot(first.X()-last.X(), first.Y()-last.Y()) < 1e-8,
                    "unexpected nonaxial seam edge")
            require(all(abs(a-b) < 1e-8 for a,b in zip(
                    sorted((first.Z(), last.Z())), (0,20))), "seam does not span both caps")
            seam_radii.append(math.hypot(first.X(), first.Y()))
    require(len(circle_radii) == 4 and all(abs(a-b) < 1e-8 for a,b in
            zip(sorted(circle_radii), (5,5,10,10))), "tube rings were lost or changed")
    require(len(seam_radii) == 2 and all(abs(a-b) < 1e-8 for a,b in
            zip(sorted(seam_radii), (5,10))), "missing inner or outer periodic seam")
    volume, area = measure(shape, True), measure(shape, False)
    require(math.isclose(volume, 1500*math.pi, rel_tol=1e-9), "wrong tube volume")
    require(math.isclose(area, 750*math.pi, rel_tol=1e-9), "wrong tube boundary area")
    return {"topology": counts, "volume_mm3": volume, "area_mm2": area,
            "cylinder_radii_mm": sorted(radii), "cap_z_mm": sorted(caps),
            "annular_cap_wire_counts": [2,2], "seam_representations": seam_representations,
            "brep_valid": True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_tube_step.py <native.step> <exported.step>")
    native, _ = read_step(Path(sys.argv[1]))
    exported, _ = read_step(Path(sys.argv[2]))
    native_report, exported_report = check_tube_shape(native), check_tube_shape(exported)
    differences = compare_solids(native, exported)
    print(json.dumps({"ocp_distribution_version": importlib.metadata.version("cadquery-ocp"),
                      "native_reference": native_report, "library_export": exported_report,
                      "bidirectional_difference_volume_mm3": differences}, indent=2))


if __name__ == "__main__":
    main()
