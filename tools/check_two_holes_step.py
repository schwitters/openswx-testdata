#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Check both R3 bores, with unique geometric ownership, in 40 x 30 x 20 stock."""
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

from step_check import axial_seam_data, compare_solids, measure, read_step, require, topology_counts

CENTERS = ((10,15),(30,15))
CORNERS = tuple(itertools.product((0,40),(0,30),(0,20)))


def identify_center(x,y):
    matches = [center for center in CENTERS if math.dist((x,y),center) < 1e-8]
    require(len(matches) == 1,"wrong or ambiguous bore position")
    return matches[0]


def check_two_holes_shape(shape):
    counts = topology_counts(shape)
    require(counts["faces"] == 8 and counts["solids"] == 1,"incomplete two-hole solid")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    cylinders,planes = {},[]
    for index in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(index))
        surface = BRepAdaptor_Surface(face)
        if surface.GetType() == GeomAbs_Cylinder:
            cylinder = surface.Cylinder()
            require(abs(cylinder.Radius()-3) < 1e-8,"wrong bore radius")
            axis = cylinder.Axis()
            require(abs(abs(axis.Direction().Z())-1) < 1e-12,"wrong bore axis")
            center = identify_center(axis.Location().X(),axis.Location().Y())
            require(center not in cylinders,"duplicate bore ownership")
            cylinders[center] = face
        else:
            require(surface.GetType() == GeomAbs_Plane,"nonplanar stock face")
            plane = surface.Plane()
            direction = plane.Axis().Direction()
            components = (direction.X(),direction.Y(),direction.Z())
            axis = max(range(3),key=lambda i:abs(components[i]))
            require(abs(abs(components[axis])-1) < 1e-12,"oblique stock face")
            p = plane.Location()
            coordinate = (p.X(),p.Y(),p.Z())[axis]
            explorer,wires = TopExp_Explorer(face,TopAbs_WIRE),0
            while explorer.More():
                wires += 1
                explorer.Next()
            planes.append((axis,coordinate,wires))
    expected_planes = ((0,0,1),(0,40,1),(1,0,1),(1,30,1),(2,0,3),(2,20,3))
    require(set(cylinders) == set(CENTERS) and len(planes) == 6 and all(
            a[0] == b[0] and abs(a[1]-b[1]) < 1e-8 and a[2] == b[2]
            for a,b in zip(sorted(planes),expected_planes)),"wrong stock bounds or cap loops")
    remaining = set(CORNERS)
    ring_vertices = {center:[] for center in CENTERS}
    for index in range(1,vertices.Extent()+1):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(index)))
        point = (p.X(),p.Y(),p.Z())
        matches = [corner for corner in remaining if math.dist(point,corner) < 1e-8]
        if matches:
            remaining.remove(matches[0])
        else:
            owners = [center for center in CENTERS if abs(math.dist(point[:2],center)-3) < 1e-8]
            require(len(owners) == 1,"ambiguous ring vertex ownership")
            ring_vertices[owners[0]].append(point[2])
    require(not remaining,"lost outer stock corner")
    for values in ring_vertices.values():
        require(len(values) == 2 and all(abs(a-b) < 1e-8 for a,b in zip(sorted(values),(0,20))),
                "lost rim seam vertex")
    rings = {center:[] for center in CENTERS}
    seams,lines = {},0
    for index in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(index))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType() == GeomAbs_Circle:
            circle = curve.Circle()
            center = identify_center(circle.Location().X(),circle.Location().Y())
            require(abs(circle.Radius()-3) < 1e-8 and
                    abs(abs(circle.Axis().Direction().Z())-1) < 1e-12 and
                    abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi) < 1e-12,
                    "wrong circular rim")
            rings[center].append(circle.Location().Z())
        else:
            owners = [center for center,face in cylinders.items() if BRep_Tool.IsClosed_s(edge,face)]
            if owners:
                require(len(owners) == 1 and owners[0] not in seams,"ambiguous bore seam ownership")
                center = owners[0]
                seams[center] = axial_seam_data(edge,curve,[cylinders[center]],axis_xy=center)
            else:
                require(curve.GetType() == GeomAbs_Line,"nonlinear stock edge")
                for t in (curve.FirstParameter(),curve.LastParameter()):
                    p = curve.Value(t)
                    require(any(math.dist((p.X(),p.Y(),p.Z()),corner) < 1e-8 for corner in CORNERS),
                            "stock edge lost its corner")
                lines += 1
    require(lines == 12 and set(seams) == set(CENTERS),"lost stock edge or bore seam")
    for center in CENTERS:
        require(len(rings[center]) == 2 and all(abs(a-b) < 1e-8 for a,b in zip(sorted(rings[center]),(0,20))),
                "a bore does not open through both caps")
        require(abs(seams[center]["radius_mm"]-3) < 1e-8 and all(abs(a-b) < 1e-8
                for a,b in zip(seams[center]["z_span_mm"],(0,20))),"wrong bore seam span")
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,24000-360*math.pi,rel_tol=1e-9),"wrong two-hole volume")
    require(math.isclose(area,5200+204*math.pi,rel_tol=1e-9),"wrong two-hole area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,
            "stock_plane_axis_position_wire_count":sorted(planes),
            "bores":[{"center_xy_mm":center,"ring_z_mm":sorted(rings[center]),"seam":seams[center]} for center in CENTERS],
            "brep_valid":True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_two_holes_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    native_report,exported_report = check_two_holes_shape(native),check_two_holes_shape(exported)
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":native_report,"library_export":exported_report,
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__ == "__main__":
    main()
