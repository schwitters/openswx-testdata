#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify a 90-degree R20/r5 torus segment and its meridional end disks."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakeTorus
from OCP.BRepTools import BRepTools
from OCP.ElSLib import ElSLib
from OCP.Geom2d import Geom2d_Line
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Circle, GeomAbs_Plane, GeomAbs_Torus
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_OUT, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt, gp_Pnt2d

from bezier_check import bezier_radial_bound
from step_check import compare_solids, measure, read_step, require, topology_counts

CENTERS = ((20,0,0),(0,20,0))
TOLERANCE_MM = 1e-5


def xyz(point):
    return (point.X(),point.Y(),point.Z())


def classify_torus(face,surface,point):
    u,v = ElSLib.Parameters_s(surface.Torus(),point)
    a,b,c,d = BRepTools.UVBounds_s(face)
    # Keep the point's periodic equivalent near the trimmed, possibly unwrapped UV chart.
    u += 2*math.pi*round(((a+b)/2-u)/(2*math.pi))
    v += 2*math.pi*round(((c+d)/2-v)/(2*math.pi))
    return BRepClass_FaceClassifier(face,gp_Pnt2d(u,v),1e-8).State()


def circle_owner(point):
    matches = [i for i,center in enumerate(CENTERS) if abs(math.dist(xyz(point),center)-5)<1e-8 and
               abs(point.Y() if i==0 else point.X())<1e-8]
    require(len(matches)==1,"vertex has wrong meridional-circle ownership")
    return matches[0]


def check_parallel_seam(edge,curve,face,surface):
    pcurve = BRep_Tool.CurveOnSurface_s(edge,face,0.,0.)
    require(isinstance(pcurve,Geom2d_Line) and abs(pcurve.Direction().Y())<1e-12,
            "torus segment seam lacks an exact constant-V pcurve")
    first,last = BRep_Tool.Range_s(edge,face)
    uv = [pcurve.Value(t) for t in (first,last)]
    require(abs(abs(uv[1].X()-uv[0].X())-math.pi/2)<1e-12,"wrong seam angular interval")
    support_ends = [surface.Value(p.X(),p.Y()) for p in uv]
    require({circle_owner(p) for p in support_ends}=={0,1},"seam does not connect both cut circles")
    center = (0,0,support_ends[0].Z())
    radius = math.hypot(support_ends[0].X(),support_ends[0].Y())
    ends = [curve.Value(t) for t in (curve.FirstParameter(),curve.LastParameter())]
    require(all(any(p.Distance(q)<TOLERANCE_MM for q in ends) for p in support_ends),"seam endpoints disagree with exact torus pcurve")
    if curve.GetType()==GeomAbs_Circle:
        circle = curve.Circle()
        require(abs(circle.Radius()-radius)<1e-8 and math.dist(xyz(circle.Location()),center)<1e-8 and
                abs(abs(circle.Axis().Direction().Z())-1)<1e-12 and
                abs(curve.LastParameter()-curve.FirstParameter()-math.pi/2)<1e-12,"wrong analytic parallel seam")
        return {"representation":"circle","radius_mm":radius,"z_mm":center[2]}
    require(curve.GetType()==GeomAbs_BSplineCurve,"unexpected torus seam basis")
    spline = curve.BSpline()
    n = spline.Degree()
    require(not spline.IsPeriodic() and spline.NbPoles()==n+1 and spline.NbKnots()==2 and
            spline.Multiplicity(1)==n+1 and spline.Multiplicity(2)==n+1 and
            abs(curve.FirstParameter()-spline.FirstParameter())<1e-12 and
            abs(curve.LastParameter()-spline.LastParameter())<1e-12,
            "importer seam must be one complete Bezier")
    poles = [xyz(spline.Pole(i)) for i in range(1,spline.NbPoles()+1)]
    weights = [spline.Weight(i) for i in range(1,spline.NbPoles()+1)]
    require(all(x>=-1e-8 and y>=-1e-8 and abs(z-center[2])<1e-8 for x,y,z in poles),
            "Bezier seam leaves its first-quadrant parallel plane")
    bound = bezier_radial_bound(poles,center,radius,weights)
    require(bound<=min(TOLERANCE_MM,BRep_Tool.Tolerance_s(edge)),"Bezier seam radial bound exceeds tolerance")
    return {"representation":"occt_rational_bezier" if spline.IsRational() else "occt_polynomial_bezier",
            "degree":n,"poles_mm":poles,"weights":weights,"radius_mm":radius,"z_mm":center[2],
            "exact_torus_pcurve":True,"radial_deviation_bound_mm":bound,
            "edge_tolerance_mm":BRep_Tool.Tolerance_s(edge)}


def check_torus_cut_shape(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":3,"edges":3,"vertices":2,"solids":1},"incomplete torus segment")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    torus_face=torus_surface=None
    planes=set()
    for i in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
        if surface.GetType()==GeomAbs_Torus:
            require(torus_face is None,"duplicate torus face")
            torus_face,torus_surface=face,surface
            torus = surface.Torus()
            require(abs(torus.MajorRadius()-20)<1e-8 and abs(torus.MinorRadius()-5)<1e-8,
                    "wrong torus segment radii")
            require(math.dist(xyz(torus.Location()),(0,0,0))<1e-8 and
                    abs(abs(torus.Axis().Direction().Z())-1)<1e-12,"wrong torus segment center or axis")
            a,b,c,d = BRepTools.UVBounds_s(face)
            require(abs(b-a-math.pi/2)<1e-12 and abs(d-c-2*math.pi)<1e-12,"wrong torus segment UV span")
            for fu in (.125,.375,.625,.875):
                for fv in (0,.25,.5,.75):
                    u,v=a+(b-a)*fu,c+(d-c)*fv
                    point=surface.Value(u,v)
                    x,y,z=xyz(point);rho=math.hypot(x,y)
                    require(x>0 and y>0 and abs((rho-20)**2+z*z-25)<1e-8,"wrong torus quadrant or surface")
                    props=BRepLProp_SLProps(surface,u,v,1,1e-10)
                    require(props.IsNormalDefined(),"undefined torus segment normal")
                    actual=tuple(sign*n for n in xyz(props.Normal()))
                    expected=((rho-20)*x/(5*rho),(rho-20)*y/(5*rho),z/5)
                    require(math.dist(actual,expected)<1e-10,"wrong torus segment material normal")
            for angle,expected in ((math.pi/4,TopAbs_IN),(math.pi,TopAbs_OUT),(-math.pi/2,TopAbs_OUT)):
                point=gp_Pnt(25*math.cos(angle),25*math.sin(angle),0)
                require(classify_torus(face,surface,point) in ((TopAbs_IN,TopAbs_ON) if expected==TopAbs_IN else (TopAbs_OUT,)),
                        "wrong torus angular trim")
        else:
            require(surface.GetType()==GeomAbs_Plane,"unexpected segment surface family")
            plane=surface.Plane();direction=plane.Axis().Direction()
            normal=tuple(sign*n for n in xyz(direction))
            owners=[i for i,n in enumerate(((0,-1,0),(-1,0,0))) if math.dist(normal,n)<1e-10]
            require(len(owners)==1 and owners[0] not in planes,"wrong or duplicate cut-face material normal")
            owner=owners[0];planes.add(owner)
            require(abs(plane.Location().Y() if owner==0 else plane.Location().X())<1e-8,"wrong radial cutting plane")
            for z,state in ((0,TopAbs_IN),(6,TopAbs_OUT)):
                p=gp_Pnt(CENTERS[owner][0],CENTERS[owner][1],z)
                uv=ElSLib.Parameters_s(plane,p)
                require(BRepClass_FaceClassifier(face,gp_Pnt2d(*uv),1e-8).State()==state,"wrong meridional disk trim")
    require(torus_face is not None and planes=={0,1},"missing torus mantle or radial cap")
    rings=set();seams=[]
    for i in range(1,edges.Extent()+1):
        edge=TopoDS.Edge_s(edges.FindKey(i))
        require(not BRep_Tool.Degenerated_s(edge),"torus segment has a degenerate edge")
        curve=BRepAdaptor_Curve(edge)
        if BRep_Tool.IsClosed_s(edge,torus_face):
            seams.append(check_parallel_seam(edge,curve,torus_face,torus_surface))
        else:
            require(curve.GetType()==GeomAbs_Circle,"meridional cut edge is not circular")
            circle=curve.Circle();center=xyz(circle.Location())
            owners=[i for i,p in enumerate(CENTERS) if math.dist(center,p)<1e-8]
            require(len(owners)==1 and owners[0] not in rings,"wrong or duplicate meridional ring center")
            owner=owners[0];rings.add(owner)
            axis=xyz(circle.Axis().Direction());expected=(0,1,0) if owner==0 else (1,0,0)
            require(abs(circle.Radius()-5)<1e-8 and abs(abs(sum(a*b for a,b in zip(axis,expected)))-1)<1e-12 and
                    abs(curve.LastParameter()-curve.FirstParameter()-2*math.pi)<1e-12,"wrong meridional circle radius, axis or interval")
    require(rings=={0,1} and len(seams)==1,"lost cut circle or periodic tube seam")
    require({circle_owner(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i)))) for i in range(1,vertices.Extent()+1)}=={0,1},
            "missing a cut-ring seam vertex")
    volume,area=measure(shape,True),measure(shape,False)
    require(math.isclose(volume,250*math.pi**2,rel_tol=1e-9),"wrong torus segment volume")
    require(math.isclose(area,100*math.pi**2+50*math.pi,rel_tol=1e-9),"wrong torus segment area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"angle_rad":math.pi/2,
            "quadrant":"positive_x_positive_y","meridional_circle_centers_mm":CENTERS,
            "seam":seams[0],"trim_membership_verified":True,"outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: check_torus_cut_step.py <native.step>")
    native,_=read_step(Path(sys.argv[1]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_torus_cut_shape(native),
                      "analytic_reference_difference_volume_mm3":compare_solids(native,BRepPrimAPI_MakeTorus(20,5,math.pi/2).Shape()),
                      "library_export":"not_produced"},indent=2))


if __name__=="__main__":
    main()
