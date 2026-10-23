#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify a C2 top-rim chamfer on an R10/H20 cylinder, in millimetres."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepFilletAPI import BRepFilletAPI_MakeChamfer
from OCP.BRepGProp import BRepGProp
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepTools import BRepTools
from OCP.ElSLib import ElSLib
from OCP.Geom2d import Geom2d_Line, Geom2d_TrimmedCurve
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Line, GeomAbs_Plane, GeomAbs_Cone
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_OUT, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt, gp_Pnt2d

from step_check import axial_seam_data, compare_solids, measure, read_step, require, topology_counts


def xyz(point):
    return (point.X(),point.Y(),point.Z())


def make_chamfer(top=True,distance=2):
    stock = BRepPrimAPI_MakeCylinder(10,20).Shape()
    edges = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(stock,TopAbs_EDGE,edges)
    candidates = []
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType()==GeomAbs_Circle and abs(curve.Circle().Location().Z()-(20 if top else 0))<1e-8:
            candidates.append(edge)
    require(len(candidates)==1,"ambiguous kernel chamfer rim")
    chamfer = BRepFilletAPI_MakeChamfer(stock)
    chamfer.Add(distance,candidates[0])
    chamfer.Build()
    require(chamfer.IsDone(),"kernel reference chamfer failed")
    return chamfer.Shape()


def check_chamfer_meridian(edge,curve,face,surface):
    pcurve = BRep_Tool.CurveOnSurface_s(edge,face,0.,0.)
    basis = pcurve.BasisCurve() if isinstance(pcurve,Geom2d_TrimmedCurve) else pcurve
    require(isinstance(basis,Geom2d_Line) and abs(basis.Direction().X())<1e-12,
            "chamfer seam lacks an exact constant-U cone pcurve")
    first,last = BRep_Tool.Range_s(edge,face)
    support_ends = [surface.Value(pcurve.Value(t).X(),pcurve.Value(t).Y()) for t in (first,last)]
    if curve.GetType()==GeomAbs_BSplineCurve:
        spline=curve.BSpline()
        require(spline.Degree()==1 and spline.NbPoles()==2 and not spline.IsRational(),
                "uncertified chamfer generator spline")
        representation="polynomial_degree_1_bspline"
    else:
        require(curve.GetType()==GeomAbs_Line,"chamfer generator is not straight")
        representation="line"
    ends=[curve.Value(t) for t in (curve.FirstParameter(),curve.LastParameter())]
    require(all(any(p.Distance(q)<1e-8 for q in ends) for p in support_ends),"chamfer generator disagrees with pcurve")
    require(all(math.dist(a,b)<1e-8 for a,b in zip(sorted((p.Z(),math.hypot(p.X(),p.Y())) for p in ends),((18,10),(20,8)))),
            "chamfer generator does not connect both rings")
    directions=[(p.X()/math.hypot(p.X(),p.Y()),p.Y()/math.hypot(p.X(),p.Y())) for p in ends]
    require(math.dist(*directions)<1e-10,"generator crosses the cone interior")
    return {"representation":representation,"z_span_mm":[18,20],"radius_span_mm":[10,8],"exact_cone_pcurve":True}


def check_chamfer_shape(shape):
    require(BRepCheck_Analyzer(shape).IsValid(),"invalid chamfer B-rep")
    counts = topology_counts(shape)
    require(counts=={"faces":4,"edges":5,"vertices":3,"solids":1},"incomplete chamfered cylinder")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    cone_face=cone_surface=cylinder_face=None
    planes=[]
    for i in range(1,faces.Extent()+1):
        face=TopoDS.Face_s(faces.FindKey(i));surface=BRepAdaptor_Surface(face)
        sign=1 if face.Orientation()==TopAbs_FORWARD else -1
        kind=surface.GetType()
        if kind==GeomAbs_Plane:
            plane=surface.Plane();z=plane.Location().Z()
            require(any(abs(z-target)<1e-8 for target in (0,20)),"wrong chamfer cap placement")
            target=0 if abs(z)<1e-8 else 20
            require(abs(sign*plane.Axis().Direction().Z()-(-1 if target==0 else 1))<1e-12,"wrong chamfer cap material normal")
            radius=10 if target==0 else 8
            for point,state in ((gp_Pnt(0,0,z),TopAbs_IN),(gp_Pnt(radius+1,0,z),TopAbs_OUT)):
                uv=ElSLib.Parameters_s(plane,point)
                require(BRepClass_FaceClassifier(face,gp_Pnt2d(*uv),1e-8).State()==state,"wrong chamfer cap trim")
            planes.append(target)
            continue
        a,b,c,d=BRepTools.UVBounds_s(face)
        require(abs(b-a-2*math.pi)<1e-12,"chamfer rotational face is not a full turn")
        if kind==GeomAbs_Cylinder:
            require(cylinder_face is None,"duplicate cylinder support")
            cylinder_face=face;cylinder=surface.Cylinder()
            require(abs(cylinder.Radius()-10)<1e-8 and math.hypot(cylinder.Location().X(),cylinder.Location().Y())<1e-8 and
                    abs(abs(cylinder.Axis().Direction().Z())-1)<1e-12,"wrong cylinder support")
        else:
            require(kind==GeomAbs_Cone and cone_face is None,"unexpected chamfer support family")
            cone_face,cone_surface=face,surface;cone=surface.Cone()
            require(abs(abs(cone.SemiAngle())-math.pi/4)<1e-12 and
                    math.hypot(cone.Location().X(),cone.Location().Y())<1e-8 and
                    abs(abs(cone.Axis().Direction().Z())-1)<1e-12,"wrong chamfer cone angle or axis")
            for point,state in ((gp_Pnt(9,0,19),TopAbs_IN),(gp_Pnt(11,0,17),TopAbs_OUT),(gp_Pnt(7,0,21),TopAbs_OUT)):
                u,v=ElSLib.Parameters_s(cone,point)
                u+=2*math.pi*round(((a+b)/2-u)/(2*math.pi))
                actual=BRepClass_FaceClassifier(face,gp_Pnt2d(u,v),1e-8).State()
                require(actual in ((TopAbs_IN,TopAbs_ON) if state==TopAbs_IN else (TopAbs_OUT,)),"wrong chamfer cone trim")
        z_values=[]
        for fu in (0,.25,.5,.75):
            for fv in (0,.5,1):
                u,v=a+(b-a)*fu,c+(d-c)*fv
                point=surface.Value(u,v);x,y,z=xyz(point);rho=math.hypot(x,y)
                if kind==GeomAbs_Cylinder:
                    require(abs(rho-10)<1e-8 and -1e-8<=z<=18+1e-8,"wrong remaining cylinder interval")
                    expected=(x/rho,y/rho,0)
                else:
                    require(8-1e-8<=rho<=10+1e-8 and 18-1e-8<=z<=20+1e-8 and
                            abs(rho-(28-z))<1e-8,"wrong chamfer straight profile")
                    expected=(x/rho/math.sqrt(2),y/rho/math.sqrt(2),1/math.sqrt(2))
                props=BRepLProp_SLProps(surface,u,v,1,1e-10)
                require(props.IsNormalDefined(),"undefined chamfer normal")
                require(math.dist(tuple(sign*n for n in xyz(props.Normal())),expected)<1e-10,"wrong chamfer material normal")
                z_values.append(z)
        require(abs(min(z_values)-(0 if kind==GeomAbs_Cylinder else 18))<1e-8 and
                abs(max(z_values)-(18 if kind==GeomAbs_Cylinder else 20))<1e-8,"lost chamfer axial extent")
    require(sorted(planes)==[0,20] and cylinder_face is not None and cone_face is not None,"missing chamfer face")
    rings=[];axial=[];meridians=[]
    for i in range(1,edges.Extent()+1):
        edge=TopoDS.Edge_s(edges.FindKey(i));require(not BRep_Tool.Degenerated_s(edge),"unexpected degenerate chamfer edge")
        curve=BRepAdaptor_Curve(edge)
        if BRep_Tool.IsClosed_s(edge,cone_face):
            meridians.append(check_chamfer_meridian(edge,curve,cone_face,cone_surface))
        elif BRep_Tool.IsClosed_s(edge,cylinder_face):
            seam=axial_seam_data(edge,curve,[cylinder_face])
            require(abs(seam["radius_mm"]-10)<1e-8 and all(abs(a-b)<1e-8 for a,b in zip(seam["z_span_mm"],(0,18))),"wrong chamfer axial seam")
            axial.append(seam)
        else:
            require(curve.GetType()==GeomAbs_Circle,"noncircular chamfer ring")
            circle=curve.Circle();p=circle.Location()
            require(math.hypot(p.X(),p.Y())<1e-8 and abs(abs(circle.Axis().Direction().Z())-1)<1e-12 and
                    abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi)<1e-12,"wrong chamfer ring center, axis or interval")
            rings.append((p.Z(),circle.Radius()))
    require(len(rings)==3 and all(math.dist(a,b)<1e-8 for a,b in zip(sorted(rings),((0,10),(18,10),(20,8)))),"wrong chamfer ring radii or association")
    require(len(axial)==1 and len(meridians)==1,"lost chamfer import seam")
    remaining=[(0,10),(18,10),(20,8)]
    for i in range(1,vertices.Extent()+1):
        p=BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i)))
        matches=[target for target in remaining if math.dist((p.Z(),math.hypot(p.X(),p.Y())),target)<1e-8]
        require(len(matches)==1,"wrong or duplicate chamfer ring vertex")
        remaining.remove(matches[0])
    volume,area=measure(shape,True),measure(shape,False)
    require(math.isclose(volume,5888*math.pi/3,rel_tol=1e-9),"wrong chamfer volume")
    require(math.isclose(area,(524+36*math.sqrt(2))*math.pi,rel_tol=1e-9),"wrong chamfer area")
    properties=GProp_GProps();BRepGProp.VolumeProperties_s(shape,properties,Eps=1e-12)
    center=xyz(properties.CentreOfMass());expected_z=57836/5888
    require(math.dist(center,(0,0,expected_z))<1e-8,"wrong chamfer centroid")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"centroid_mm":center,
            "surface_families":{"plane":2,"cylinder":1,"cone":1},"ring_z_radius_mm":sorted(rings),
            "axial_seam":axial[0],"chamfer_generator":meridians[0],"outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: check_chamfer_step.py <native.step> <exported.step>")
    native,_=read_step(Path(sys.argv[1]));exported,_=read_step(Path(sys.argv[2]))
    kernel=make_chamfer()
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_chamfer_shape(native),"library_export":check_chamfer_shape(exported),
                      "analytic_kernel_reference":check_chamfer_shape(kernel),
                      "native_kernel_difference_volume_mm3":compare_solids(native,kernel),
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__=="__main__":
    main()
