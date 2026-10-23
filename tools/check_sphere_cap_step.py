#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify an R10 sphere cap above Z=5 mm, allowing certified importer seams."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool, BRep_Builder
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepBuilderAPI import BRepBuilderAPI_Copy
from OCP.Geom import Geom_Circle
from OCP.GeomProjLib import GeomProjLib
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.ElSLib import ElSLib
from OCP.Geom2d import Geom2d_Line
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_Circle, GeomAbs_Plane, GeomAbs_Sphere
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_ON, TopAbs_OUT, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt, gp_Pnt2d

from step_check import compare_solids, measure, read_step, require, topology_counts

RIM_RADIUS = math.sqrt(75)
TOLERANCE_MM = 1e-5  # Same length as the 1e-8 metre source binding tolerance.


def xyz(point):
    return (point.X(),point.Y(),point.Z())


def spherical_bezier_radial_bound(poles):
    """Bound radial deviation over a whole polynomial Bezier via Bernstein products."""
    degree = len(poles)-1
    require(1<=degree<=7 and all(len(p)==3 and all(math.isfinite(v) for v in p) for p in poles),
            "invalid importer Bezier poles")
    coefficients = []
    for k in range(2*degree+1):
        terms = [math.comb(degree,i)*math.comb(degree,k-i)/math.comb(2*degree,k)*
                 math.fsum(a*b for a,b in zip(poles[i],poles[k-i]))
                 for i in range(max(0,k-degree),min(degree,k)+1)]
        coefficients.append(math.fsum(terms)-100)
    # Convex-hull bound on squared radius, with a conservative roundoff allowance.
    squared_bound = max(abs(v) for v in coefficients)+1e-9
    require(squared_bound<100,"unbounded importer meridian")
    return squared_bound/(math.sqrt(100-squared_bound)+10)


def classify(face,surface,point):
    support = surface.Sphere() if surface.GetType()==GeomAbs_Sphere else surface.Plane()
    return BRepClass_FaceClassifier(face,gp_Pnt2d(*ElSLib.Parameters_s(support,point)),1e-8).State()


def check_meridian(edge,curve,face,surface):
    require(BRep_Tool.IsClosed_s(edge,face),"extra edge is not a spherical seam")
    pcurve = BRep_Tool.CurveOnSurface_s(edge,face,0.,0.)
    require(isinstance(pcurve,Geom2d_Line) and abs(pcurve.Direction().X())<1e-12,
            "seam lacks an exact constant-U sphere pcurve")
    first,last = BRep_Tool.Range_s(edge,face)
    support_ends = [surface.Value(pcurve.Value(t).X(),pcurve.Value(t).Y()) for t in (first,last)]
    require(all(abs(a-b)<1e-8 for a,b in zip(sorted(p.Z() for p in support_ends),(5,10))),
            "meridian does not connect rim and pole")
    ends = [curve.Value(t) for t in (curve.FirstParameter(),curve.LastParameter())]
    require(all(any(p.Distance(q)<TOLERANCE_MM for q in ends) for p in support_ends),
            "3D seam endpoints disagree with exact pcurve")
    if curve.GetType()==GeomAbs_Circle:
        circle = curve.Circle()
        require(abs(circle.Radius()-10)<1e-8 and math.dist(xyz(circle.Location()),(0,0,0))<1e-8,
                "wrong analytic meridian circle")
        require(abs(curve.LastParameter()-curve.FirstParameter()-math.pi/3)<1e-12,
                "analytic meridian does not retain the short cap interval")
        return {"representation":"circle","radial_deviation_bound_mm":0}
    require(curve.GetType()==GeomAbs_BSplineCurve,"unexpected meridian basis")
    spline = curve.BSpline()
    n = spline.Degree()
    require(not spline.IsRational() and not spline.IsPeriodic() and spline.NbPoles()==n+1 and
            spline.NbKnots()==2 and spline.Multiplicity(1)==n+1 and spline.Multiplicity(2)==n+1 and
            abs(curve.FirstParameter()-spline.FirstParameter())<1e-12 and
            abs(curve.LastParameter()-spline.LastParameter())<1e-12,
            "importer meridian must be one complete polynomial Bezier")
    poles = [xyz(spline.Pole(i)) for i in range(1,spline.NbPoles()+1)]
    rim = min(support_ends,key=lambda p:p.Z())
    direction = (rim.X()/RIM_RADIUS,rim.Y()/RIM_RADIUS)
    for x,y,z in poles:
        require(abs(x*direction[1]-y*direction[0])<1e-8 and
                x*direction[0]+y*direction[1]>=-1e-8 and 5-1e-8<=z<=10+1e-8,
                "importer Bezier leaves its meridian half-plane or cap")
    bound = spherical_bezier_radial_bound(poles)
    require(bound<=min(TOLERANCE_MM,BRep_Tool.Tolerance_s(edge)),
            "importer Bezier radial bound exceeds declared tolerance")
    return {"representation":"occt_polynomial_bezier","degree":n,"poles_mm":poles,
            "exact_sphere_pcurve":True,"radial_deviation_bound_mm":bound,
            "edge_tolerance_mm":BRep_Tool.Tolerance_s(edge)}


def check_sphere_cap_shape(shape,check_measures=True):
    counts = topology_counts(shape)
    require(counts["faces"]==2 and counts["solids"]==1,"incomplete sphere cap")
    faces,edges,vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    TopExp.MapShapes_s(shape,TopAbs_VERTEX,vertices)
    sphere_face=sphere_surface=None
    planes=0
    for i in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
        explorer,wires = TopExp_Explorer(face,TopAbs_WIRE),0
        while explorer.More():
            wires += 1
            explorer.Next()
        require(wires==1,"unexpected cap hole or split face wire")
        if surface.GetType()==GeomAbs_Sphere:
            require(sphere_face is None,"duplicate spherical support")
            sphere_face,sphere_surface=face,surface
            sphere = surface.Sphere()
            require(abs(sphere.Radius()-10)<1e-8 and math.dist(xyz(sphere.Location()),(0,0,0))<1e-8,
                    "wrong cap sphere radius or center")
            for z in (6,8,9.5):
                r = math.sqrt(100-z*z)
                for angle in (0,math.pi/2,math.pi,3*math.pi/2):
                    point = gp_Pnt(r*math.cos(angle),r*math.sin(angle),z)
                    require(classify(face,surface,point) in (TopAbs_IN,TopAbs_ON),"missing cap surface region")
                    u,v = ElSLib.Parameters_s(sphere,point)
                    props = BRepLProp_SLProps(surface,u,v,1,1e-10)
                    require(props.IsNormalDefined(),"undefined regular cap normal")
                    normal = tuple(sign*n for n in xyz(props.Normal()))
                    require(math.dist(normal,tuple(x/10 for x in xyz(point)))<1e-10,
                            "wrong spherical cap material normal")
            require(classify(face,surface,gp_Pnt(0,0,10)) in (TopAbs_IN,TopAbs_ON),
                    "sphere cap loses its north pole")
            for point in (gp_Pnt(10,0,0),gp_Pnt(math.sqrt(75),0,-5)):
                require(classify(face,surface,point)==TopAbs_OUT,"sphere trim extends below cap")
        else:
            require(surface.GetType()==GeomAbs_Plane,"unexpected cap surface family")
            plane = surface.Plane()
            require(abs(plane.Location().Z()-5)<1e-8,"wrong cap cutting plane")
            require(abs(sign*plane.Axis().Direction().Z()+1)<1e-12,"wrong cap base material normal")
            for point,expected in ((gp_Pnt(0,0,5),TopAbs_IN),(gp_Pnt(RIM_RADIUS+1,0,5),TopAbs_OUT)):
                require(classify(face,surface,point)==expected,"wrong base disk trim")
            planes += 1
    require(sphere_face is not None and planes==1,"missing sphere or base")
    intervals,seams,degenerate = [],[],0
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        if BRep_Tool.Degenerated_s(edge):
            vs = TopTools_IndexedMapOfShape()
            TopExp.MapShapes_s(edge,TopAbs_VERTEX,vs)
            require(vs.Extent()==1 and math.dist(xyz(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vs.FindKey(1)))),(0,0,10))<1e-8,
                    "degenerate cap edge is not at the north pole")
            degenerate += 1
        else:
            curve = BRepAdaptor_Curve(edge)
            if BRep_Tool.IsClosed_s(edge,sphere_face):
                seams.append(check_meridian(edge,curve,sphere_face,sphere_surface))
                continue
            require(curve.GetType()==GeomAbs_Circle,"noncircular cap rim")
            circle = curve.Circle()
            require(abs(circle.Radius()-RIM_RADIUS)<1e-8 and math.dist(xyz(circle.Location()),(0,0,5))<1e-8 and
                    abs(abs(circle.Axis().Direction().Z())-1)<1e-12,"wrong cap rim geometry")
            span = curve.LastParameter()-curve.FirstParameter()
            require(0<span<=2*math.pi+1e-12,"wrong rim interval")
            if abs(span-2*math.pi)<1e-12:
                intervals.append((0,2*math.pi))
            else:
                p = curve.Value(curve.FirstParameter())
                start = (math.atan2(p.Y(),p.X())-(span if circle.Axis().Direction().Z()<0 else 0))%(2*math.pi)
                end = start+span
                if end>2*math.pi+1e-12:
                    intervals.extend(((start,2*math.pi),(0,end-2*math.pi)))
                else:
                    intervals.append((start,min(end,2*math.pi)))
    endpoint=0
    for start,end in sorted(intervals):
        require(abs(start-endpoint)<1e-10,"overlapping or missing rim angular interval")
        endpoint=end
    require(abs(endpoint-2*math.pi)<1e-10,"incomplete cap rim")
    rim_vertices=pole_vertices=0
    for i in range(1,vertices.Extent()+1):
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i)))
        if abs(p.Z()-5)<1e-8 and abs(math.hypot(p.X(),p.Y())-RIM_RADIUS)<1e-8:
            rim_vertices += 1
        else:
            require(math.dist(xyz(p),(0,0,10))<1e-8,"unexpected cap vertex")
            pole_vertices += 1
    arcs = edges.Extent()-len(seams)-degenerate
    require(arcs in (1,2) and rim_vertices==arcs and
            ((len(seams)==0 and degenerate==0 and pole_vertices==0) or
             (len(seams)==1 and degenerate==1 and pole_vertices==1)),"unexplained cap import topology")
    volume,area = measure(shape,True),measure(shape,False)
    if check_measures:
        require(math.isclose(volume,625*math.pi/3,rel_tol=1e-9),"wrong cap volume")
        require(math.isclose(area,175*math.pi,rel_tol=1e-9),"wrong cap area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,"base_z_mm":5,
            "sphere_radius_mm":10,"rim_radius_mm":RIM_RADIUS,"rim_arc_count":arcs,
            "degenerate_pole_edges":degenerate,"seams":seams,"trim_membership_verified":True,
            "outward_normals_verified":True,"brep_valid":True}


def repair_native_cap_pcurve(shape):
    """Repair only the observed reference-import projection, on a deep copy."""
    original = check_sphere_cap_shape(shape,check_measures=False)
    require(original["topology"]=={"faces":2,"edges":1,"vertices":1,"solids":1},
            "native cap reference topology changed; review projection workaround")
    copied = BRepBuilderAPI_Copy(shape,True,False).Shape()
    faces,edges = TopTools_IndexedMapOfShape(),TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(copied,TopAbs_FACE,faces)
    TopExp.MapShapes_s(copied,TopAbs_EDGE,edges)
    face = next(TopoDS.Face_s(faces.FindKey(i)) for i in range(1,faces.Extent()+1)
                if BRepAdaptor_Surface(TopoDS.Face_s(faces.FindKey(i))).GetType()==GeomAbs_Sphere)
    surface = BRepAdaptor_Surface(face)
    edge = TopoDS.Edge_s(edges.FindKey(1))
    curve = BRepAdaptor_Curve(edge)
    require(curve.GetType()==GeomAbs_Circle,"native rim must remain an exact 3D circle")
    first,last = BRep_Tool.Range_s(edge,face)
    def correspondence_error(pcurve):
        return max(surface.Value(pcurve.Value(t).X(),pcurve.Value(t).Y()).Distance(curve.Value(t))
                   for t in (first+(last-first)*i/1024 for i in range(1025)))
    original_error = correspondence_error(BRep_Tool.CurveOnSurface_s(edge,face,0.,0.))
    tolerance = BRep_Tool.Tolerance_s(edge)
    report = {"raw_import":original,"raw_max_sampled_pcurve_error_mm":original_error,
              "edge_tolerance_mm":tolerance,"projection_rebuilt":False}
    if original_error>tolerance:
        require(tolerance<=TOLERANCE_MM,"native edge tolerance exceeds fixture tolerance")
        pcurve = GeomProjLib.Curve2d_s(Geom_Circle(curve.Circle()),curve.FirstParameter(),
                                     curve.LastParameter(),BRep_Tool.Surface_s(face),1e-10)
        require(pcurve is not None,"precise reference rim projection failed")
        repaired_error = correspondence_error(pcurve)
        repaired_tolerance = max(tolerance,2*repaired_error)
        require(repaired_tolerance<=TOLERANCE_MM,"reference projection exceeds fixture binding tolerance")
        BRep_Builder().UpdateEdge(edge,pcurve,face,repaired_tolerance)
        report.update(projection_rebuilt=True,requested_projection_tolerance_mm=1e-10,
                      repaired_max_sampled_pcurve_error_mm=repaired_error,
                      repaired_edge_tolerance_mm=BRep_Tool.Tolerance_s(edge))
    # Always require strict analytic measures and valid topology after projection.
    check_sphere_cap_shape(copied)
    return copied,report


def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: check_sphere_cap_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    corrected,import_report = repair_native_cap_pcurve(native)
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_sphere_cap_shape(corrected),
                      "native_reference_import":import_report,
                      "library_export":check_sphere_cap_shape(exported),
                      "original_import_difference_volume_mm3":compare_solids(native,exported),
                      "bidirectional_difference_volume_mm3":compare_solids(corrected,exported)},indent=2))


if __name__=="__main__":
    main()
