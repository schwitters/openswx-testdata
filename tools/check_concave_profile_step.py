#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify a six-edge L-profile, including its reentrant cap trims and normals."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import (TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN,
                        TopAbs_OUT, TopAbs_VERTEX, TopAbs_WIRE)
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt

from step_check import compare_solids, measure, read_step, require, topology_counts

PROFILE = ((0,0),(40,0),(40,10),(15,10),(15,30),(0,30))
CORNERS = tuple((x,y,z) for z in (0,20) for x,y in PROFILE)


def point_tuple(point):
    return (point.X(),point.Y(),point.Z())


def identify_corner(point):
    matches = [p for p in CORNERS if math.dist(point,p) < 1e-8]
    require(len(matches) == 1,"wrong L-profile dimension or placement")
    return matches[0]


def vertex_set(shape):
    vertices = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    return frozenset(identify_corner(point_tuple(BRep_Tool.Pnt_s(
        TopoDS.Vertex_s(vertices.FindKey(i))))) for i in range(1,vertices.Extent()+1))


def check_concave_profile_shape(shape):
    counts = topology_counts(shape)
    require(counts == {"faces":8,"edges":18,"vertices":12,"solids":1},
            "incomplete L-profile topology")
    require(vertex_set(shape) == frozenset(CORNERS),"lost L-profile corner")
    segments = [(PROFILE[i],PROFILE[(i+1)%6]) for i in range(6)]
    expected_edges = {frozenset(((a[0],a[1],z),(b[0],b[1],z)))
                      for a,b in segments for z in (0,20)}
    expected_edges.update(frozenset(((x,y,0),(x,y,20))) for x,y in PROFILE)
    edges,faces = TopTools_IndexedMapOfShape(),TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        curve = BRepAdaptor_Curve(edge)
        require(curve.GetType() == GeomAbs_Line,"nonlinear L-profile edge")
        pair = frozenset(identify_corner(point_tuple(curve.Value(t))) for t in
                         (curve.FirstParameter(),curve.LastParameter()))
        require(pair in expected_edges,"wrong L-profile edge connectivity")
        expected_edges.remove(pair)
    require(not expected_edges,"lost L-profile edge")
    expected_faces = {}
    for a,b in segments:
        boundary = frozenset((p[0],p[1],z) for p in (a,b) for z in (0,20))
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        expected_faces[boundary] = (dy/length,-dx/length,0)
    for z in (0,20):
        expected_faces[frozenset((x,y,z) for x,y in PROFILE)] = (0,0,-1 if z==0 else 1)
    caps = []
    for i in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        require(surface.GetType() == GeomAbs_Plane,"nonplanar L-profile face")
        boundary = vertex_set(face)
        require(boundary in expected_faces,"wrong L-profile face connectivity")
        expected_normal = expected_faces.pop(boundary)
        direction = surface.Plane().Axis().Direction()
        sign = 1 if face.Orientation() == TopAbs_FORWARD else -1
        normal = tuple(sign*x for x in (direction.X(),direction.Y(),direction.Z()))
        require(math.dist(normal,expected_normal) < 1e-10,"wrong material face normal")
        explorer,wires = TopExp_Explorer(face,TopAbs_WIRE),0
        while explorer.More():
            wires += 1
            explorer.Next()
        require(wires == 1,"unexpected L-profile cap hole or split wire")
        if len(boundary) == 6:
            z = next(iter(boundary))[2]
            # Points cover both legs, their overlap and the removed rectangle.
            for x,y,expected in ((5,5,TopAbs_IN),(30,5,TopAbs_IN),(5,25,TopAbs_IN),
                                 (20,15,TopAbs_OUT),(35,25,TopAbs_OUT)):
                classified = BRepClass_FaceClassifier(face,gp_Pnt(x,y,z),1e-8)
                require(classified.State() == expected,"wrong concave cap trim membership")
            caps.append(z)
    require(not expected_faces and sorted(caps)==[0,20],"lost L-profile cap or side")
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,14000,rel_tol=1e-9),"wrong L-profile volume")
    require(math.isclose(area,4200,rel_tol=1e-9),"wrong L-profile boundary area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,
            "profile_xy_mm":PROFILE,"cap_z_mm":sorted(caps),
            "reentrant_corner_xy_mm":[15,10],"cap_trim_membership_verified":True,
            "outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_concave_profile_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_concave_profile_shape(native),
                      "library_export":check_concave_profile_shape(exported),
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__ == "__main__":
    main()
