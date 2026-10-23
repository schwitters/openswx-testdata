#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify each explicitly selected body against a two-body native STEP part."""
import importlib.metadata
import itertools
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_SOLID, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import compare_solids, measure, read_step, require, topology_counts

SPECS = {"large-block": ((0,0,0),(20,30,40)),
         "small-block": ((50,0,0),(10,15,20))}


def check_selected_block(shape,key):
    counts = topology_counts(shape)
    require(counts=={"faces":6,"edges":12,"vertices":8,"solids":1},
            "selection must export exactly one complete block")
    origin,size = SPECS[key]
    corners = set(itertools.product(*[(a,a+b) for a,b in zip(origin,size)]))
    vertices,edges,faces = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    def corner(point):
        value = (point.X(),point.Y(),point.Z())
        matches = [c for c in corners if math.dist(value,c)<1e-8]
        require(len(matches)==1,"wrong selected body dimensions or placement")
        return matches[0]
    actual = {corner(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))))
              for i in range(1,vertices.Extent()+1)}
    require(actual==corners,"lost selected body corner")
    expected_edges = {frozenset((a,b)) for a in corners for b in corners
                      if sum(x!=y for x,y in zip(a,b))==1}
    for i in range(1,edges.Extent()+1):
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
        require(curve.GetType()==GeomAbs_Line,"nonlinear block edge")
        pair = frozenset(corner(curve.Value(t)) for t in (curve.FirstParameter(),curve.LastParameter()))
        require(pair in expected_edges,"wrong selected edge connectivity")
        expected_edges.remove(pair)
    require(not expected_edges,"lost selected body edge")
    expected_planes = {(axis,side) for axis in range(3) for side in (0,1)}
    for i in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        require(surface.GetType()==GeomAbs_Plane,"nonplanar block face")
        plane = surface.Plane()
        direction = plane.Axis().Direction()
        sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
        normal = tuple(sign*x for x in (direction.X(),direction.Y(),direction.Z()))
        axis = max(range(3),key=lambda a:abs(normal[a]))
        require(abs(abs(normal[axis])-1)<1e-12,"oblique block face")
        side = int(normal[axis]>0)
        point = plane.Location()
        value = (point.X(),point.Y(),point.Z())[axis]
        require(abs(value-origin[axis]-side*size[axis])<1e-8 and
                (axis,side) in expected_planes,"wrong selected face position or material normal")
        expected_planes.remove((axis,side))
    require(not expected_planes,"lost selected body plane")
    w,d,h = size
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,w*d*h,rel_tol=1e-9),"wrong selected body volume")
    require(math.isclose(area,2*(w*d+w*h+d*h),rel_tol=1e-9),"wrong selected body area")
    return {"key":key,"topology":counts,"origin_mm":origin,"size_mm":size,
            "volume_mm3":volume,"area_mm2":area,"brep_valid":True}


def native_bodies(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":12,"edges":24,"vertices":16,"solids":2},
            "native reference must contain both disjoint blocks")
    solids = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape,TopAbs_SOLID,solids)
    remaining = set(SPECS)
    matched = {}
    for i in range(1,solids.Extent()+1):
        solid = TopoDS.Solid_s(solids.FindKey(i))
        keys = []
        for key in remaining:
            try:
                check_selected_block(solid,key)
                keys.append(key)
            except RuntimeError:
                pass
        require(len(keys)==1,"wrong or duplicate native body ownership")
        key = keys[0]
        remaining.remove(key)
        matched[key] = solid
    require(not remaining,"missing native body")
    return matched


def check_multiple_solids(native,exports):
    require(set(exports)==set(SPECS),"both explicit body exports are required")
    bodies = native_bodies(native)
    reports = []
    builder,combined = BRep_Builder(),TopoDS_Compound()
    builder.MakeCompound(combined)
    for key in SPECS:
        exported = exports[key]
        report = check_selected_block(exported,key)
        report["bidirectional_difference_volume_mm3"] = compare_solids(bodies[key],exported)
        reports.append(report)
        builder.Add(combined,exported)
    return {"native_topology":topology_counts(native),"body_exports":reports,
            "combined_topology":topology_counts(combined),
            "bidirectional_difference_volume_mm3":compare_solids(native,combined)}


def main():
    if len(sys.argv)!=4:
        raise SystemExit("Usage: check_multiple_solids_step.py <native.step> <large.step> <small.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exports = {key:read_step(Path(path))[0] for key,path in zip(SPECS,sys.argv[2:])}
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      **check_multiple_solids(native,exports)},indent=2))


if __name__=="__main__":
    main()
