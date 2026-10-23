#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Validate the native reference of an X/Y=10/5, H20 mm elliptic prism."""
import importlib.metadata
import json
import math
from pathlib import Path
import sys

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepGProp import BRepGProp
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.BRepTools import BRepTools
from OCP.ElSLib import ElSLib
from OCP.GCPnts import GCPnts_AbscissaPoint
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_BSplineSurface, GeomAbs_Ellipse, GeomAbs_Line, GeomAbs_Plane, GeomAbs_SurfaceOfExtrusion
from OCP.GeomConvert import GeomConvert_BSplineCurveToBezierCurve
from OCP.GProp import GProp_GProps
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Ax2, gp_Dir, gp_Elips, gp_Pnt, gp_Pnt2d, gp_Vec

from bezier_check import bezier_radial_bound
from step_check import compare_solids, measure, read_step, require, topology_counts


def coordinates(point):
    return (point.X(),point.Y(),point.Z())


def make_elliptic_prism(major=10,minor=5,height=20):
    ellipse = gp_Elips(gp_Ax2(gp_Pnt(0,0,0),gp_Dir(0,0,1)),major,minor)
    wire = BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(ellipse).Edge()).Wire()
    return BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire).Face(),gp_Vec(0,0,height)).Shape()


def ellipse_spline_bound(spline,z):
    """Certify every rational Bezier span after scaling Y to a radius-10 circle."""
    converter = GeomConvert_BSplineCurveToBezierCurve(spline)
    bounds=[]
    for index in range(1,converter.NbArcs()+1):
        arc=converter.Arc(index)
        poles=[(arc.Pole(i).X(),2*arc.Pole(i).Y(),arc.Pole(i).Z()-z)
               for i in range(1,arc.NbPoles()+1)]
        weights=[arc.Weight(i) for i in range(1,arc.NbPoles()+1)]
        bound=bezier_radial_bound(poles,(0,0,0),10,weights)
        require(bound<=1e-5,"spline departs from the ellipse")
        require(all(abs(p[2])<1e-8 for p in poles),"ellipse spline is not planar")
        bounds.append(bound)
    require(bounds,"empty ellipse spline")
    return max(bounds)


def check_ring(curve):
    first,last=curve.FirstParameter(),curve.LastParameter()
    require(math.isfinite(first) and math.isfinite(last) and last>first,"invalid ellipse interval")
    z=curve.Value(first).Z()
    require(min(abs(z),abs(z-20))<1e-8,"wrong ellipse end plane")
    require(curve.Value(first).Distance(curve.Value(last))<1e-8,"ellipse is not closed")
    bound=0
    if curve.GetType()==GeomAbs_Ellipse:
        ellipse=curve.Ellipse()
        require(abs(ellipse.MajorRadius()-10)<1e-8 and abs(ellipse.MinorRadius()-5)<1e-8 and
                abs(abs(ellipse.XAxis().Direction().X())-1)<1e-12 and
                math.hypot(ellipse.Location().X(),ellipse.Location().Y())<1e-8 and
                abs(abs(ellipse.Axis().Direction().Z())-1)<1e-12,"wrong ellipse axes or center")
        require(abs(last-first-2*math.pi)<1e-12,"ellipse does not cover one turn")
        representation="ellipse"
    else:
        require(curve.GetType()==GeomAbs_BSplineCurve,"unexpected ellipse boundary family")
        bound=ellipse_spline_bound(curve.BSpline(),z)
        representation="rational_bspline"
    # Whole-curve bounds alone do not certify full coverage or traversal count.
    angles=[]
    for i in range(257):
        x,y,actual_z=coordinates(curve.Value(first+(last-first)*i/256))
        require(abs(actual_z-z)<1e-8 and abs(math.hypot(x,2*y)-10)<1e-5,"wrong ellipse placement")
        angle=math.atan2(2*y,x)
        if angles:
            angle+=2*math.pi*round((angles[-1]-angle)/(2*math.pi))
        angles.append(angle)
    require(abs(abs(angles[-1]-angles[0])-2*math.pi)<1e-10,"ellipse winding is not one full turn")
    perimeter=GCPnts_AbscissaPoint.Length_s(curve,first,last,1e-10)
    require(abs(perimeter-48.44224110273838)<1e-8,"wrong ellipse perimeter")
    return {"z_mm":z,"representation":representation,"scaled_radial_bound_mm":bound,"perimeter_mm":perimeter}


def check_mantle(surface,face):
    u0,u1,v0,v1=BRepTools.UVBounds_s(face)
    kind=surface.GetType()
    bound=0
    if kind==GeomAbs_BSplineSurface:
        spline=surface.BSpline()
        require(spline.VDegree()==1 and spline.NbVPoles()==2,"mantle is not a linear extrusion")
        require(all(abs(a-b)<1e-12 for a,b in zip((u0,u1,v0,v1),spline.Bounds())),
                "mantle does not retain its full support domain")
        end_planes=[]
        for v in (1,2):
            values=[spline.Pole(u,v).Z() for u in range(1,spline.NbUPoles()+1)]
            require(max(values)-min(values)<1e-8,"extrusion poles are not coplanar")
            end_planes.append(values[0])
        require(all(abs(a-b)<1e-8 for a,b in zip(sorted(end_planes),(0,20))),"wrong extrusion pole planes")
        for u in range(1,spline.NbUPoles()+1):
            first,last=spline.Pole(u,1),spline.Pole(u,2)
            require(math.hypot(first.X()-last.X(),first.Y()-last.Y())<1e-10 and
                    math.isclose(spline.Weight(u,1),spline.Weight(u,2),rel_tol=1e-12),
                    "mantle is tapered, twisted or has varying extrusion weights")
        bound=ellipse_spline_bound(spline.VIso(v0),end_planes[0])
        # Certify full ellipse traversal on the support, independently of its edges.
        check_ring(BRepAdaptor_Curve(BRepBuilderAPI_MakeEdge(spline.VIso(v0)).Edge()))
        representation="linear_rational_bspline_surface"
    else:
        require(kind==GeomAbs_SurfaceOfExtrusion,"unexpected elliptic mantle support")
        require(abs(abs(surface.Direction().Z())-1)<1e-12,"oblique elliptic extrusion")
        check_ring(surface.BasisCurve())
        representation="surface_of_extrusion"
    sign=1 if face.Orientation()==TopAbs_FORWARD else -1
    heights=[]
    for fu in (0,.125,.25,.375,.5,.625,.75,.875,1):
        for fv in (0,.5,1):
            u,v=u0+(u1-u0)*fu,v0+(v1-v0)*fv
            x,y,z=coordinates(surface.Value(u,v));heights.append(z)
            require(abs(math.hypot(x,2*y)-10)<1e-5 and -1e-8<=z<=20+1e-8,"wrong elliptic mantle position")
            gradient=(x/100,y/25,0);length=math.hypot(*gradient)
            expected=tuple(n/length for n in gradient)
            props=BRepLProp_SLProps(surface,u,v,1,1e-10)
            require(props.IsNormalDefined() and math.dist(tuple(sign*n for n in coordinates(props.Normal())),expected)<1e-8,
                    "wrong elliptic mantle material normal")
    require(abs(min(heights))<1e-8 and abs(max(heights)-20)<1e-8,"wrong extrusion height")
    return {"representation":representation,"scaled_radial_bound_mm":bound,"linear_extrusion_verified":True}


def check_elliptic_shape(shape):
    counts=topology_counts(shape)
    require(counts=={"faces":3,"edges":3,"vertices":2,"solids":1},"incomplete elliptic prism")
    faces,edges,vertices=(TopTools_IndexedMapOfShape() for _ in range(3))
    for kind,mapping in ((TopAbs_FACE,faces),(TopAbs_EDGE,edges),(TopAbs_VERTEX,vertices)):
        TopExp.MapShapes_s(shape,kind,mapping)
    planes=[];mantle=None;support=None
    for i in range(1,faces.Extent()+1):
        face=TopoDS.Face_s(faces.FindKey(i));surface=BRepAdaptor_Surface(face)
        if surface.GetType()!=GeomAbs_Plane:
            require(mantle is None,"duplicate elliptic mantle")
            mantle=face;support=check_mantle(surface,face)
            continue
        plane=surface.Plane();z=plane.Location().Z();sign=1 if face.Orientation()==TopAbs_FORWARD else -1
        require(min(abs(z),abs(z-20))<1e-8,"wrong elliptic cap plane")
        require(abs(sign*plane.Axis().Direction().Z()-(-1 if abs(z)<1e-8 else 1))<1e-12,
                "wrong elliptic cap material normal")
        for point,state in ((gp_Pnt(0,0,z),TopAbs_IN),(gp_Pnt(9,4,z),TopAbs_OUT)):
            uv=ElSLib.Parameters_s(plane,point)
            require(BRepClass_FaceClassifier(face,gp_Pnt2d(*uv),1e-8).State()==state,"wrong elliptic cap trim")
        planes.append(z)
    require(len(planes)==2 and all(abs(a-b)<1e-8 for a,b in zip(sorted(planes),(0,20))) and mantle is not None,
            "missing elliptic cap or mantle")
    rings=[];seams=[]
    for i in range(1,edges.Extent()+1):
        edge=TopoDS.Edge_s(edges.FindKey(i));curve=BRepAdaptor_Curve(edge)
        require(not BRep_Tool.Degenerated_s(edge),"degenerate elliptic edge")
        if not BRep_Tool.IsClosed_s(edge,mantle):
            rings.append(check_ring(curve));continue
        if curve.GetType()==GeomAbs_BSplineCurve:
            spline=curve.BSpline()
            require(spline.Degree()==1 and spline.NbPoles()==2 and not spline.IsRational(),"uncertified extrusion seam")
            representation="polynomial_degree_1_bspline"
        else:
            require(curve.GetType()==GeomAbs_Line,"extrusion seam is not straight")
            representation="line"
        ends=[coordinates(curve.Value(t)) for t in (curve.FirstParameter(),curve.LastParameter())]
        require(math.dist(ends[0][:2],ends[1][:2])<1e-8 and
                all(abs(a-b)<1e-8 for a,b in zip(sorted(p[2] for p in ends),(0,20))) and
                all(abs(math.hypot(p[0],2*p[1])-10)<1e-5 for p in ends),"wrong elliptic axial seam")
        seams.append(representation)
    require(len(rings)==2 and len(seams)==1 and
            all(abs(a-b)<1e-8 for a,b in zip(sorted(r['z_mm'] for r in rings),(0,20))),"wrong elliptic edge inventory")
    heights=[]
    for i in range(1,vertices.Extent()+1):
        x,y,z=coordinates(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))))
        require(abs(math.hypot(x,2*y)-10)<1e-5,"vertex off ellipse")
        heights.append(z)
    require(all(abs(a-b)<1e-8 for a,b in zip(sorted(heights),(0,20))),"wrong elliptic vertices")
    properties=GProp_GProps()
    estimated_error=BRepGProp.VolumePropertiesGK_s(shape,properties,1e-12,True,True,True,False,False)
    volume=properties.Mass();center=coordinates(properties.CentreOfMass())
    require(0<=estimated_error<1e-9 and math.isclose(volume,1000*math.pi,rel_tol=1e-9),"wrong elliptic volume")
    require(math.dist(center,(0,0,10))<1e-8,"wrong elliptic centroid")
    # The certified straight extrusion gives area from perimeter and exact caps.
    area=100*math.pi+20*rings[0]['perimeter_mm']
    require(abs(area-1283.004087413747)<1e-8,"wrong elliptic boundary-derived area")
    return {"topology":counts,"volume_mm3":volume,"volume_gk_estimated_relative_error":estimated_error,
            "centroid_mm":center,"boundary_derived_area_mm2":area,
            "occt_default_quadrature_area_mm2":measure(shape,False),
            "mantle":support,"rings":rings,"axial_seam_representation":seams[0],
            "outward_normals_verified":True,"brep_valid":True}


def main():
    if len(sys.argv)!=2:
        raise SystemExit("Usage: check_elliptic_profile_step.py <native.step>")
    native,_=read_step(Path(sys.argv[1]));kernel=make_elliptic_prism()
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version('cadquery-ocp'),
        "native_reference":check_elliptic_shape(native),"analytic_kernel_reference":check_elliptic_shape(kernel),
        "native_kernel_difference_volume_mm3":compare_solids(native,kernel),
        "step_equivalence":"not_tested_no_library_output"},indent=2))


if __name__=='__main__':
    main()
