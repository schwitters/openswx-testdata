#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Validate the native complete-sphere STEP oracle, including natural boundaries."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Sphere
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import compare_solids, measure, read_step, require, topology_counts


def coordinates(point):
    return (point.X(),point.Y(),point.Z())


def check_sphere_shape(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":1,"edges":3,"vertices":2,"solids":1},"incomplete natural sphere")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    face = TopoDS.Face_s(faces.FindKey(1))
    surface = BRepAdaptor_Surface(face)
    require(surface.GetType()==GeomAbs_Sphere,"wrong sphere support family")
    sphere = surface.Sphere()
    require(abs(sphere.Radius()-10)<1e-8 and math.dist(coordinates(sphere.Location()),(0,0,0))<1e-8,
            "wrong sphere radius or placement")
    a,b,c,d = BRepTools.UVBounds_s(face)
    require(abs(b-a-2*math.pi)<1e-12 and abs(c+math.pi/2)<1e-12 and abs(d-math.pi/2)<1e-12,
            "sphere does not cover the complete angular domain")
    sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
    for fu in (.125,.375,.625,.875):
        for v in (-math.pi/4,0,math.pi/4):
            u = a+(b-a)*fu
            point = coordinates(surface.Value(u,v))
            require(abs(math.sqrt(sum(x*x for x in point))-10)<1e-8,"sphere sample leaves analytic support")
            props = BRepLProp_SLProps(surface,u,v,1,1e-10)
            require(props.IsNormalDefined(),"undefined regular sphere normal")
            n = props.Normal()
            actual = tuple(sign*v for v in coordinates(n))
            require(math.dist(actual,tuple(x/10 for x in point))<1e-10,"wrong sphere material normal")
    # Pole locations belong to the support frame, not a fixed document axis.
    axis = coordinates(sphere.Position().Direction())
    poles = [tuple(sign*10*x for x in axis) for sign in (-1,1)]
    unmatched = list(poles)
    for i in range(1,vertices.Extent()+1):
        point = coordinates(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))))
        matches = [p for p in unmatched if math.dist(point,p)<1e-8]
        require(len(matches)==1,"wrong or duplicate sphere pole vertex")
        unmatched.remove(matches[0])
    require(not unmatched,"missing sphere pole")
    degenerate_poles,seams = [],0
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        if BRep_Tool.Degenerated_s(edge):
            pole_vertices = TopTools_IndexedMapOfShape()
            TopExp.MapShapes_s(edge,TopAbs_VERTEX,pole_vertices)
            require(pole_vertices.Extent()==1,"degenerate pole edge must collapse to one vertex")
            point = coordinates(BRep_Tool.Pnt_s(TopoDS.Vertex_s(pole_vertices.FindKey(1))))
            matches = [j for j,pole in enumerate(poles) if math.dist(point,pole)<1e-8]
            require(len(matches)==1,"degenerate edge leaves its pole")
            degenerate_poles.append(matches[0])
        else:
            require(BRep_Tool.IsClosed_s(edge,face),"nonperiodic sphere seam")
            curve = BRepAdaptor_Curve(edge)
            require(curve.GetType()==GeomAbs_Circle,"sphere seam is not an exact meridian circle")
            circle = curve.Circle()
            require(abs(circle.Radius()-10)<1e-8 and math.dist(coordinates(circle.Location()),(0,0,0))<1e-8,
                    "wrong sphere meridian circle")
            require(abs(curve.LastParameter()-curve.FirstParameter()-math.pi)<1e-12,"wrong meridian angular interval")
            endpoints = [coordinates(curve.Value(t)) for t in (curve.FirstParameter(),curve.LastParameter())]
            require(all(any(math.dist(p,pole)<1e-8 for p in endpoints) for pole in poles),
                    "meridian does not connect both poles")
            seams += 1
    require(sorted(degenerate_poles)==[0,1] and seams==1,"missing natural sphere boundaries")
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,4000*math.pi/3,rel_tol=1e-9),"wrong sphere volume")
    require(math.isclose(area,400*math.pi,rel_tol=1e-9),"wrong sphere area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"radius_mm":10,
            "support_pole_axis":axis,"degenerate_pole_edges":2,"periodic_meridian_seams":1,
            "outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: check_sphere_step.py <native.step>")
    native,_ = read_step(Path(sys.argv[1]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_sphere_shape(native),
                      "analytic_reference_difference_volume_mm3":compare_solids(native,BRepPrimAPI_MakeSphere(10).Shape()),
                      "library_export":"not_produced"},indent=2))


if __name__=="__main__":
    main()
