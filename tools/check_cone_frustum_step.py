#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify an R10/R5, 20 mm cone frustum and its imported generatrix seam."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Circle, GeomAbs_Cone, GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt

from step_check import compare_solids, measure, read_step, require, topology_counts


def check_frustum_point(point):
    x,y,z = point.X(),point.Y(),point.Z()
    radius = math.hypot(x,y)
    require(-1e-8<=z<=20+1e-8 and abs(radius-(10-.25*z))<1e-8,
            "wrong frustum radius law or placement")
    return x,y,z,radius


def check_conical_seam(edge,curve,cone_face):
    require(BRep_Tool.IsClosed_s(edge,cone_face),"extra edge is not a periodic cone seam")
    if curve.GetType()==GeomAbs_BSplineCurve:
        spline = curve.BSpline()
        require(spline.Degree()==1 and spline.NbPoles()==2 and not spline.IsRational(),
                "uncertified conical seam spline")
        representation = "polynomial_degree_1_bspline"
    else:
        require(curve.GetType()==GeomAbs_Line,"unexpected conical seam basis")
        representation = "line"
    ends = [check_frustum_point(curve.Value(t)) for t in (curve.FirstParameter(),curve.LastParameter())]
    require(all(abs(a-b)<1e-8 for a,b in zip(sorted(p[2] for p in ends),(0,20))),
            "conical seam does not span both rims")
    directions = [(p[0]/p[3],p[1]/p[3]) for p in ends]
    require(math.dist(*directions)<1e-10,"seam crosses the cone interior")
    return {"z_span_mm":sorted(p[2] for p in ends),"representation":representation}


def check_cone_frustum_shape(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":3,"edges":3,"vertices":2,"solids":1},"incomplete cone frustum")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    cone_face,caps = None,[]
    for i in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
        if surface.GetType()==GeomAbs_Cone:
            require(cone_face is None,"duplicate conical mantle")
            cone_face = face
            cone = surface.Cone()
            require(abs(abs(cone.SemiAngle())-math.atan(.25))<1e-12,"wrong cone half angle")
            require(abs(abs(cone.Axis().Direction().Z())-1)<1e-12 and
                    math.hypot(cone.Axis().Location().X(),cone.Axis().Location().Y())<1e-8,
                    "wrong cone axis or placement")
            a,b,c,d = BRepTools.UVBounds_s(face)
            for fu in (.125,.375,.625,.875):
                for fv in (.25,.75):
                    u,v = a+(b-a)*fu,c+(d-c)*fv
                    x,y,z,radius = check_frustum_point(surface.Value(u,v))
                    props = BRepLProp_SLProps(surface,u,v,1,1e-10)
                    require(props.IsNormalDefined(),"undefined conical normal")
                    n = props.Normal()
                    actual = tuple(sign*v for v in (n.X(),n.Y(),n.Z()))
                    expected = (x/radius/math.sqrt(1+.25**2),y/radius/math.sqrt(1+.25**2),.25/math.sqrt(1+.25**2))
                    require(math.dist(actual,expected)<1e-10,"wrong cone material normal")
        else:
            require(surface.GetType()==GeomAbs_Plane,"unexpected frustum surface")
            plane = surface.Plane()
            z = plane.Location().Z()
            require(any(abs(z-target)<1e-8 for target in (0,20)),"wrong cap placement")
            target_z = 0 if abs(z)<1e-8 else 20
            direction = plane.Axis().Direction()
            require(abs(sign*direction.Z()-(-1 if target_z==0 else 1))<1e-12,
                    "wrong cap material normal")
            radius = 10 if target_z==0 else 5
            for point,expected in ((gp_Pnt(0,0,z),TopAbs_IN),(gp_Pnt(radius+1,0,z),TopAbs_OUT)):
                require(BRepClass_FaceClassifier(face,point,1e-8).State()==expected,"wrong cap trim")
            explorer,wires = TopExp_Explorer(face,TopAbs_WIRE),0
            while explorer.More():
                wires += 1
                explorer.Next()
            require(wires==1,"unexpected frustum cap hole")
            caps.append(target_z)
    require(cone_face is not None and sorted(caps)==[0,20],"lost mantle or cap")
    rings,seams = [],[]
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType()==GeomAbs_Circle:
            circle = curve.Circle()
            p = circle.Location()
            require(math.hypot(p.X(),p.Y())<1e-8 and abs(abs(circle.Axis().Direction().Z())-1)<1e-12,
                    "wrong rim center or axis")
            require(abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi)<1e-12,"incomplete circular rim")
            rings.append((p.Z(),circle.Radius()))
        else:
            seams.append(check_conical_seam(edge,curve,cone_face))
    require(len(rings)==2 and all(math.dist(a,b)<1e-8 for a,b in zip(sorted(rings),((0,10),(20,5)))),
            "wrong rim radii or cap association")
    require(len(seams)==1,"missing conical seam")
    zs = []
    for i in range(1,vertices.Extent()+1):
        point = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i)))
        zs.append(check_frustum_point(point)[2])
    require(all(abs(a-b)<1e-8 for a,b in zip(sorted(zs),(0,20))),"lost rim seam vertex")
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,3500*math.pi/3,rel_tol=1e-9),"wrong frustum volume")
    require(math.isclose(area,math.pi*(125+75*math.sqrt(17)),rel_tol=1e-9),"wrong frustum area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"ring_z_radius_mm":sorted(rings),
            "cone_half_angle_rad":math.atan(.25),"outward_normals_verified":True,"seam":seams[0],"brep_valid":True}


def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: check_cone_frustum_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_cone_frustum_shape(native),
                      "library_export":check_cone_frustum_shape(exported),
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__=="__main__":
    main()
