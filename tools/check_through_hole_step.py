#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Check the R5 through bore at (10,15) in the 20 x 30 x 40 mm block."""
import importlib.metadata
import itertools
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import (axial_seam_data, compare_solids, measure, read_step,
                        require, topology_counts)


def near_corner(point):
    return any(math.dist(point, corner) < 1e-8 for corner in
               itertools.product((0,20), (0,30), (0,40)))


def check_through_hole_shape(shape):
    counts = topology_counts(shape)
    require(counts["faces"] == 7 and counts["solids"] == 1, "incomplete through-hole solid")
    faces, edges, vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    TopExp.MapShapes_s(shape, TopAbs_VERTEX, vertices)
    cylinders, planes = [], []
    for index in range(1, faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index))
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinders.append(face)
            cylinder = surface.Cylinder()
            require(abs(cylinder.Radius()-5) < 1e-8, "wrong bore radius")
            axis = cylinder.Axis()
            require(abs(abs(axis.Direction().Z())-1) < 1e-12, "wrong bore axis")
            require(math.dist((axis.Location().X(), axis.Location().Y()), (10,15)) < 1e-8,
                    "wrong bore position")
        else:
            require(surface.GetType() == GeomAbs_Plane, "nonplanar stock face")
            plane = surface.Plane()
            direction = plane.Axis().Direction()
            components = (direction.X(), direction.Y(), direction.Z())
            axis = max(range(3), key=lambda i: abs(components[i]))
            require(abs(abs(components[axis])-1) < 1e-12, "oblique stock face")
            location = plane.Location()
            coordinate = (location.X(), location.Y(), location.Z())[axis]
            explorer, wires = TopExp_Explorer(face, TopAbs_WIRE), 0
            while explorer.More():
                wires += 1
                explorer.Next()
            planes.append((axis,coordinate,wires))
    expected_planes = ((0,0,1),(0,20,1),(1,0,1),(1,30,1),(2,0,2),(2,40,2))
    require(len(cylinders) == 1 and len(planes) == 6 and
            all(a[0] == b[0] and abs(a[1]-b[1]) < 1e-8 and a[2] == b[2]
                for a,b in zip(sorted(planes), expected_planes)), "wrong stock bounds or cap holes")
    remaining = set(itertools.product((0,20), (0,30), (0,40)))
    ring_vertices = []
    for index in range(1, vertices.Extent()+1):
        point = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(index)))
        actual = (point.X(),point.Y(),point.Z())
        matches = [corner for corner in remaining if math.dist(actual,corner) < 1e-8]
        if matches:
            remaining.remove(matches[0])
        else:
            require(abs(math.hypot(actual[0]-10,actual[1]-15)-5) < 1e-8,
                    "unexpected noncorner vertex")
            ring_vertices.append(actual[2])
    require(not remaining and len(ring_vertices) == 2 and all(abs(a-b) < 1e-8
            for a,b in zip(sorted(ring_vertices),(0,40))), "lost stock corner or hole seam vertex")
    circle_z, seams, lines = [], [], 0
    for index in range(1, edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(index))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType() == GeomAbs_Circle:
            circle = curve.Circle()
            require(abs(circle.Radius()-5) < 1e-8 and
                    math.dist((circle.Location().X(),circle.Location().Y()),(10,15)) < 1e-8,
                    "wrong ring radius or position")
            require(abs(abs(circle.Axis().Direction().Z())-1) < 1e-12 and
                    abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi) < 1e-12,
                    "tilted or incomplete hole ring")
            circle_z.append(circle.Location().Z())
        elif any(BRep_Tool.IsClosed_s(edge,face) for face in cylinders):
            seams.append(axial_seam_data(edge,curve,cylinders,axis_xy=(10,15)))
        else:
            require(curve.GetType() == GeomAbs_Line, "nonlinear stock edge")
            for parameter in (curve.FirstParameter(),curve.LastParameter()):
                point = curve.Value(parameter)
                require(near_corner((point.X(),point.Y(),point.Z())), "stock edge lost its corner")
            lines += 1
    require(len(circle_z) == 2 and all(abs(a-b) < 1e-8 for a,b in zip(sorted(circle_z),(0,40))),
            "bore does not open through both caps")
    require(lines == 12 and len(seams) == 1 and abs(seams[0]["radius_mm"]-5) < 1e-8 and
            all(abs(a-b) < 1e-8 for a,b in zip(seams[0]["z_span_mm"],(0,40))), "wrong stock edges or bore seam")
    volume, area = measure(shape,True), measure(shape,False)
    require(math.isclose(volume,24000-1000*math.pi,rel_tol=1e-9), "wrong through-hole volume")
    require(math.isclose(area,5200+350*math.pi,rel_tol=1e-9), "wrong through-hole area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,
            "stock_plane_axis_position_wire_count":sorted(planes),
            "bore_center_xy_mm":[10,15],"ring_z_mm":sorted(circle_z),"seams":seams,"brep_valid":True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_through_hole_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    native_report,exported_report = check_through_hole_shape(native),check_through_hole_shape(exported)
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":native_report,"library_export":exported_report,
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__ == "__main__":
    main()
