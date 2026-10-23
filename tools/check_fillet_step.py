#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify an R2 native top-rim fillet on an R10/H20 cylinder, in millimetres."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepFilletAPI import BRepFilletAPI_MakeFillet
from OCP.BRepGProp import BRepGProp
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCP.BRepTools import BRepTools
from OCP.ElSLib import ElSLib
from OCP.Geom2d import Geom2d_Line, Geom2d_TrimmedCurve
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Circle, GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Torus
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_OUT, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt, gp_Pnt2d

from bezier_check import bezier_radial_bound
from check_torus_cut_step import classify_torus
from step_check import axial_seam_data, compare_solids, measure, read_step, require, topology_counts


def xyz(point):
    return (point.X(),point.Y(),point.Z())


def make_fillet(top=True,radius=2):
    stock = BRepPrimAPI_MakeCylinder(10,20).Shape()
    edges = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(stock,TopAbs_EDGE,edges)
    candidates = []
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType()==GeomAbs_Circle and abs(curve.Circle().Location().Z()-(20 if top else 0))<1e-8:
            candidates.append(edge)
    require(len(candidates)==1,"ambiguous kernel fillet rim")
    fillet = BRepFilletAPI_MakeFillet(stock)
    fillet.Add(radius,candidates[0])
    fillet.Build()
    require(fillet.IsDone(),"kernel reference fillet failed")
    return fillet.Shape()


def check_fillet_meridian(edge,curve,face,surface):
    pcurve = BRep_Tool.CurveOnSurface_s(edge,face,0.,0.)
    basis = pcurve.BasisCurve() if isinstance(pcurve,Geom2d_TrimmedCurve) else pcurve
    require(isinstance(basis,Geom2d_Line) and abs(basis.Direction().X())<1e-12,
            "fillet seam lacks an exact constant-U torus pcurve")
    first,last = BRep_Tool.Range_s(edge,face)
    uv = [pcurve.Value(t) for t in (first,last)]
    require(abs(abs(uv[1].Y()-uv[0].Y())-math.pi/2)<1e-12,"wrong fillet meridian interval")
    support_ends = [surface.Value(p.X(),p.Y()) for p in uv]
    require(all(math.dist(a,b)<1e-8 for a,b in zip(sorted((p.Z(),math.hypot(p.X(),p.Y())) for p in support_ends),((18,10),(20,8)))),
            "fillet seam does not connect tangent rings")
    lower = min(support_ends,key=lambda p:p.Z())
    direction = (lower.X()/10,lower.Y()/10)
    center = (8*direction[0],8*direction[1],18)
    ends = [curve.Value(t) for t in (curve.FirstParameter(),curve.LastParameter())]
    require(all(any(p.Distance(q)<1e-5 for q in ends) for p in support_ends),"fillet seam endpoints disagree with pcurve")
    if curve.GetType()==GeomAbs_Circle:
        circle = curve.Circle()
        require(abs(circle.Radius()-2)<1e-8 and math.dist(xyz(circle.Location()),center)<1e-8 and
                abs(curve.LastParameter()-curve.FirstParameter()-math.pi/2)<1e-12,"wrong analytic fillet meridian")
        return {"representation":"circle","center_mm":center,"radius_mm":2}
    require(curve.GetType()==GeomAbs_BSplineCurve,"unexpected fillet meridian basis")
    spline = curve.BSpline();n=spline.Degree()
    require(not spline.IsPeriodic() and spline.NbPoles()==n+1 and spline.NbKnots()==2 and
            spline.Multiplicity(1)==n+1 and spline.Multiplicity(2)==n+1 and
            abs(curve.FirstParameter()-spline.FirstParameter())<1e-12 and
            abs(curve.LastParameter()-spline.LastParameter())<1e-12,"fillet meridian must be one complete Bezier")
    poles = [xyz(spline.Pole(i)) for i in range(1,spline.NbPoles()+1)]
    weights = [spline.Weight(i) for i in range(1,spline.NbPoles()+1)]
    require(all(abs(x*direction[1]-y*direction[0])<1e-8 and 8-1e-8<=x*direction[0]+y*direction[1]<=10+1e-8 and
                18-1e-8<=z<=20+1e-8 for x,y,z in poles),"Bezier leaves its fillet quadrant")
    bound = bezier_radial_bound(poles,center,2,weights)
    require(bound<=min(1e-5,BRep_Tool.Tolerance_s(edge)),"fillet Bezier radial bound exceeds tolerance")
    return {"representation":"occt_rational_bezier" if spline.IsRational() else "occt_polynomial_bezier",
            "degree":n,"poles_mm":poles,"weights":weights,"center_mm":center,"radius_mm":2,
            "exact_torus_pcurve":True,"radial_deviation_bound_mm":bound,"edge_tolerance_mm":BRep_Tool.Tolerance_s(edge)}


def check_fillet_shape(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":4,"edges":5,"vertices":3,"solids":1},"incomplete filleted cylinder")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    torus_face=torus_surface=cylinder_face=None
    planes=[]
    for i in range(1,faces.Extent()+1):
        face=TopoDS.Face_s(faces.FindKey(i));surface=BRepAdaptor_Surface(face)
        sign=1 if face.Orientation()==TopAbs_FORWARD else -1
        kind=surface.GetType()
        if kind==GeomAbs_Plane:
            plane=surface.Plane();z=plane.Location().Z()
            require(any(abs(z-target)<1e-8 for target in (0,20)),"wrong fillet cap placement")
            target=0 if abs(z)<1e-8 else 20
            require(abs(sign*plane.Axis().Direction().Z()-(-1 if target==0 else 1))<1e-12,"wrong fillet cap material normal")
            radius=10 if target==0 else 8
            for point,state in ((gp_Pnt(0,0,z),TopAbs_IN),(gp_Pnt(radius+1,0,z),TopAbs_OUT)):
                uv=ElSLib.Parameters_s(plane,point)
                require(BRepClass_FaceClassifier(face,gp_Pnt2d(*uv),1e-8).State()==state,"wrong fillet cap trim")
            planes.append(target)
            continue
        a,b,c,d=BRepTools.UVBounds_s(face)
        require(abs(b-a-2*math.pi)<1e-12,"fillet rotational face is not a full turn")
        if kind==GeomAbs_Cylinder:
            require(cylinder_face is None,"duplicate cylinder support")
            cylinder_face=face;cylinder=surface.Cylinder()
            require(abs(cylinder.Radius()-10)<1e-8 and math.hypot(cylinder.Location().X(),cylinder.Location().Y())<1e-8 and
                    abs(abs(cylinder.Axis().Direction().Z())-1)<1e-12,"wrong cylinder support")
        else:
            require(kind==GeomAbs_Torus and torus_face is None,"unexpected fillet support family")
            torus_face,torus_surface=face,surface;torus=surface.Torus()
            require(abs(torus.MajorRadius()-8)<1e-8 and abs(torus.MinorRadius()-2)<1e-8 and
                    math.dist(xyz(torus.Location()),(0,0,18))<1e-8 and abs(abs(torus.Axis().Direction().Z())-1)<1e-12,
                    "wrong fillet torus radius or placement")
            require(abs(d-c-math.pi/2)<1e-12,"wrong fillet torus band span")
            for angle,state in ((math.pi/4,TopAbs_IN),(-math.pi/4,TopAbs_OUT),(3*math.pi/4,TopAbs_OUT)):
                point=gp_Pnt(8+2*math.cos(angle),0,18+2*math.sin(angle))
                require(classify_torus(face,surface,point) in ((TopAbs_IN,TopAbs_ON) if state==TopAbs_IN else (TopAbs_OUT,)),
                        "wrong fillet torus trim quadrant")
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
                            abs((rho-8)**2+(z-18)**2-4)<1e-8,"wrong fillet quarter-circle profile")
                    expected=((rho-8)*x/(2*rho),(rho-8)*y/(2*rho),(z-18)/2)
                props=BRepLProp_SLProps(surface,u,v,1,1e-10)
                require(props.IsNormalDefined(),"undefined fillet normal")
                require(math.dist(tuple(sign*n for n in xyz(props.Normal())),expected)<1e-10,"wrong fillet material normal")
                z_values.append(z)
        require(abs(min(z_values)-(0 if kind==GeomAbs_Cylinder else 18))<1e-8 and
                abs(max(z_values)-(18 if kind==GeomAbs_Cylinder else 20))<1e-8,"lost fillet axial extent")
    require(sorted(planes)==[0,20] and cylinder_face is not None and torus_face is not None,"missing fillet face")
    rings=[];axial=[];meridians=[]
    for i in range(1,edges.Extent()+1):
        edge=TopoDS.Edge_s(edges.FindKey(i));require(not BRep_Tool.Degenerated_s(edge),"unexpected degenerate fillet edge")
        curve=BRepAdaptor_Curve(edge)
        if BRep_Tool.IsClosed_s(edge,torus_face):
            meridians.append(check_fillet_meridian(edge,curve,torus_face,torus_surface))
        elif BRep_Tool.IsClosed_s(edge,cylinder_face):
            seam=axial_seam_data(edge,curve,[cylinder_face])
            require(abs(seam["radius_mm"]-10)<1e-8 and all(abs(a-b)<1e-8 for a,b in zip(seam["z_span_mm"],(0,18))),"wrong fillet axial seam")
            axial.append(seam)
        else:
            require(curve.GetType()==GeomAbs_Circle,"noncircular fillet ring")
            circle=curve.Circle();p=circle.Location()
            require(math.hypot(p.X(),p.Y())<1e-8 and abs(abs(circle.Axis().Direction().Z())-1)<1e-12 and
                    abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi)<1e-12,"wrong fillet ring center, axis or interval")
            rings.append((p.Z(),circle.Radius()))
    require(len(rings)==3 and all(math.dist(a,b)<1e-8 for a,b in zip(sorted(rings),((0,10),(18,10),(20,8)))),"wrong fillet ring radii or association")
    require(len(axial)==1 and len(meridians)==1,"lost fillet import seam")
    remaining=[(0,10),(18,10),(20,8)]
    for i in range(1,vertices.Extent()+1):
        p=BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i)))
        matches=[target for target in remaining if math.dist((p.Z(),math.hypot(p.X(),p.Y())),target)<1e-8]
        require(len(matches)==1,"wrong or duplicate fillet ring vertex")
        remaining.remove(matches[0])
    volume,area=measure(shape,True),measure(shape,False)
    require(math.isclose(volume,5800*math.pi/3+16*math.pi**2,rel_tol=1e-9),"wrong fillet volume")
    require(math.isclose(area,532*math.pi+16*math.pi**2,rel_tol=1e-9),"wrong fillet area")
    properties=GProp_GProps();BRepGProp.VolumeProperties_s(shape,properties,Eps=1e-12)
    center=xyz(properties.CentreOfMass());expected_z=(56324+864*math.pi)/(5800+48*math.pi)
    require(math.dist(center,(0,0,expected_z))<1e-8,"wrong fillet centroid")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"centroid_mm":center,
            "surface_families":{"plane":2,"cylinder":1,"torus":1},"ring_z_radius_mm":sorted(rings),
            "axial_seam":axial[0],"fillet_meridian":meridians[0],"outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: check_fillet_step.py <native.step> <exported.step>")
    native,_=read_step(Path(sys.argv[1]));exported,_=read_step(Path(sys.argv[2]))
    kernel=make_fillet()
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_fillet_shape(native),"library_export":check_fillet_shape(exported),
                      "analytic_kernel_reference":check_fillet_shape(kernel),
                      "native_kernel_difference_volume_mm3":compare_solids(native,kernel),
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__=="__main__":
    main()
