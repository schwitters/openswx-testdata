#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Validate a complete R20/r5 torus oracle and both natural periodic seams."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Torus
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import compare_solids, measure, read_step, require, topology_counts


def xyz(point):
    return (point.X(),point.Y(),point.Z())


def check_torus_shape(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":1,"edges":2,"vertices":1,"solids":1},"incomplete natural torus")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    face = TopoDS.Face_s(faces.FindKey(1))
    surface = BRepAdaptor_Surface(face)
    require(surface.GetType()==GeomAbs_Torus,"wrong torus support family")
    torus = surface.Torus()
    require(abs(torus.MajorRadius()-20)<1e-8 and abs(torus.MinorRadius()-5)<1e-8,
            "wrong torus major or minor radius")
    require(math.dist(xyz(torus.Location()),(0,0,0))<1e-8 and
            abs(abs(torus.Axis().Direction().Z())-1)<1e-12,"wrong torus center or axis")
    a,b,c,d = BRepTools.UVBounds_s(face)
    require(abs(b-a-2*math.pi)<1e-12 and abs(d-c-2*math.pi)<1e-12 and
            surface.IsUPeriodic() and surface.IsVPeriodic(),"torus must cover both complete periods")
    sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
    for fu in (0,.25,.5,.75):
        for fv in (0,.25,.5,.75):
            u,v = a+(b-a)*fu,c+(d-c)*fv
            point = surface.Value(u,v)
            x,y,z = xyz(point)
            rho = math.hypot(x,y)
            require(abs((rho-20)**2+z*z-25)<1e-8,"torus point leaves analytic support")
            props = BRepLProp_SLProps(surface,u,v,1,1e-10)
            require(props.IsNormalDefined(),"undefined regular torus normal")
            actual = tuple(sign*n for n in xyz(props.Normal()))
            expected = ((rho-20)*x/(5*rho),(rho-20)*y/(5*rho),z/5)
            require(math.dist(actual,expected)<1e-10,"wrong torus material normal")
    corner = surface.Value(a,c)
    vertex = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(1)))
    require(vertex.Distance(corner)<1e-8,"periodic seam vertex does not match support corner")
    parallels=meridians=0
    seam_reports = []
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        require(not BRep_Tool.Degenerated_s(edge) and BRep_Tool.IsClosed_s(edge,face),
                "torus edge is degenerate or not a periodic seam")
        curve = BRepAdaptor_Curve(edge)
        require(curve.GetType()==GeomAbs_Circle,"torus seam must be an exact circle")
        require(abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi)<1e-12,"incomplete seam circle")
        require(all(curve.Value(t).Distance(corner)<1e-8 for t in (curve.FirstParameter(),curve.LastParameter())),
                "seam does not close on the shared vertex")
        circle = curve.Circle()
        center,normal = circle.Location(),circle.Axis().Direction()
        if abs(abs(normal.Z())-1)<1e-12:
            require(math.hypot(center.X(),center.Y())<1e-8 and abs(center.Z()-corner.Z())<1e-8 and
                    abs(circle.Radius()-math.hypot(corner.X(),corner.Y()))<1e-8,"wrong torus parallel seam")
            parallels += 1
            kind = "parallel"
        else:
            require(abs(normal.Z())<1e-12 and abs(circle.Radius()-5)<1e-8 and
                    abs(math.hypot(center.X(),center.Y())-20)<1e-8 and abs(center.Z())<1e-8 and
                    abs(normal.X()*center.X()+normal.Y()*center.Y())<1e-8,"wrong torus meridian seam")
            meridians += 1
            kind = "meridian"
        seam_reports.append({"kind":kind,"radius_mm":circle.Radius(),"center_mm":xyz(center)})
    require(parallels==1 and meridians==1,"missing independent torus seam direction")
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,1000*math.pi**2,rel_tol=1e-9),"wrong torus volume")
    require(math.isclose(area,400*math.pi**2,rel_tol=1e-9),"wrong torus area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"major_radius_mm":20,
            "minor_radius_mm":5,"periodic_directions":2,"degenerate_edges":0,
            "seams":sorted(seam_reports,key=lambda r:r["kind"]),"outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: check_torus_step.py <native.step>")
    native,_ = read_step(Path(sys.argv[1]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_torus_shape(native),
                      "analytic_reference_difference_volume_mm3":compare_solids(native,BRepPrimAPI_MakeTorus(20,5).Shape()),
                      "library_export":"not_produced"},indent=2))


if __name__=="__main__":
    main()
