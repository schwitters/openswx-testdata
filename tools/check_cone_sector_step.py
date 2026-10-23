#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify the trims and material orientation of a first-quadrant cone sector."""
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
from OCP.ElSLib import ElSLib
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cone, GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT, TopAbs_VERTEX, TopAbs_WIRE
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.gp import gp_Pnt, gp_Pnt2d

from check_cone_frustum_step import check_frustum_point
from step_check import compare_solids, measure, read_step, require, topology_counts

BOTTOM = ((0,0,0),(10,0,0),(0,10,0))
TOP = ((0,0,20),(5,0,20),(0,5,20))
CORNERS = BOTTOM+TOP


def identify_corner(point):
    xyz = (point.X(),point.Y(),point.Z())
    matches = [p for p in CORNERS if math.dist(xyz,p)<1e-8]
    require(len(matches)==1,"wrong sector corner or angular placement")
    return matches[0]


def face_corners(face):
    vertices = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(face,TopAbs_VERTEX,vertices)
    return frozenset(identify_corner(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))))
                     for i in range(1,vertices.Extent()+1))


def classify_support_point(face,surface,point):
    # Use the underlying support: projecting onto a bounded patch can snap an
    # outside probe to its boundary and misclassify it as ON.
    support = surface.Cone() if surface.GetType()==GeomAbs_Cone else surface.Plane()
    uv = ElSLib.Parameters_s(support,point)
    return BRepClass_FaceClassifier(face,gp_Pnt2d(*uv),1e-8).State()


def check_cone_sector_shape(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":5,"edges":9,"vertices":6,"solids":1},"incomplete cone sector")
    require(face_corners(shape)==frozenset(CORNERS),"lost sector corner")
    faces,edges = TopTools_IndexedMapOfShape(),TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape,TopAbs_FACE,faces)
    TopExp.MapShapes_s(shape,TopAbs_EDGE,edges)
    o,x,y = BOTTOM
    ot,xt,yt = TOP
    expected_planes = {frozenset(BOTTOM):(0,0,-1),frozenset(TOP):(0,0,1),
                       frozenset((o,x,xt,ot)):(0,-1,0),frozenset((o,y,yt,ot)):(-1,0,0)}
    cone_face = None
    for i in range(1,faces.Extent()+1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        boundary = face_corners(face)
        sign = 1 if face.Orientation()==TopAbs_FORWARD else -1
        explorer,wires = TopExp_Explorer(face,TopAbs_WIRE),0
        while explorer.More():
            wires += 1
            explorer.Next()
        require(wires==1,"unexpected sector hole or split wire")
        if surface.GetType()==GeomAbs_Cone:
            require(cone_face is None and boundary==frozenset((x,y,xt,yt)),"wrong sector mantle boundary")
            cone_face = face
            cone = surface.Cone()
            require(abs(abs(cone.SemiAngle())-math.atan(.25))<1e-12,"wrong sector half angle")
            require(abs(abs(cone.Axis().Direction().Z())-1)<1e-12 and
                    math.hypot(cone.Axis().Location().X(),cone.Axis().Location().Y())<1e-8,
                    "wrong sector axis")
            a,b,c,d = BRepTools.UVBounds_s(face)
            for fu in (.125,.375,.625,.875):
                for fv in (.25,.75):
                    u,v = a+(b-a)*fu,c+(d-c)*fv
                    px,py,pz,radius = check_frustum_point(surface.Value(u,v))
                    require(px>0 and py>0,"wrong sector angular span")
                    props = BRepLProp_SLProps(surface,u,v,1,1e-10)
                    require(props.IsNormalDefined(),"undefined sector normal")
                    normal = props.Normal()
                    actual = [sign*n for n in (normal.X(),normal.Y(),normal.Z())]
                    expected = [px/radius/math.sqrt(1+.25**2),py/radius/math.sqrt(1+.25**2),.25/math.sqrt(1+.25**2)]
                    require(math.dist(actual,expected)<1e-10,"wrong sector material normal")
            for angle,expected in ((math.pi/4,TopAbs_IN),(math.pi,TopAbs_OUT),(-math.pi/2,TopAbs_OUT)):
                point = gp_Pnt(7.5*math.cos(angle),7.5*math.sin(angle),10)
                require(classify_support_point(face,surface,point)==expected,"wrong cone angular trim")
        else:
            require(surface.GetType()==GeomAbs_Plane and boundary in expected_planes,
                    "wrong sector plane boundary")
            expected = expected_planes.pop(boundary)
            direction = surface.Plane().Axis().Direction()
            actual = [sign*n for n in (direction.X(),direction.Y(),direction.Z())]
            require(math.dist(actual,expected)<1e-10,"wrong sector cut or cap material normal")
            # Independent trim probes use physical coordinates, not surface UV bounds.
            if abs(expected[2])==1:
                z = 0 if expected[2]<0 else 20
                radius = 10 if z==0 else 5
                probes = [(gp_Pnt(radius/4,radius/4,z),TopAbs_IN),
                          (gp_Pnt(-radius/4,radius/4,z),TopAbs_OUT),
                          (gp_Pnt(radius,radius,z),TopAbs_OUT)]
            elif expected[1]<0:
                probes = [(gp_Pnt(3,0,10),TopAbs_IN),(gp_Pnt(9,0,10),TopAbs_OUT)]
            else:
                probes = [(gp_Pnt(0,3,10),TopAbs_IN),(gp_Pnt(0,9,10),TopAbs_OUT)]
            for point,state in probes:
                require(classify_support_point(face,surface,point)==state,"wrong sector planar trim")
    require(cone_face is not None and not expected_planes,"missing sector face")
    expected_lines = {frozenset(pair) for pair in ((o,ot),(o,x),(o,y),(ot,xt),(ot,yt),(x,xt),(y,yt))}
    arcs = []
    for i in range(1,edges.Extent()+1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        curve = BRepAdaptor_Curve(edge)
        require(not BRep_Tool.IsClosed_s(edge,cone_face),"unexpected periodic sector seam")
        ends = frozenset(identify_corner(curve.Value(t)) for t in (curve.FirstParameter(),curve.LastParameter()))
        if curve.GetType()==GeomAbs_Circle:
            circle = curve.Circle()
            center = circle.Location()
            require(math.hypot(center.X(),center.Y())<1e-8 and abs(abs(circle.Axis().Direction().Z())-1)<1e-12,
                    "wrong sector arc center or axis")
            require(abs(curve.LastParameter()-curve.FirstParameter()-math.pi/2)<1e-12,"wrong circular arc span")
            require(ends in (frozenset((x,y)),frozenset((xt,yt))),"wrong sector arc endpoints")
            for f in (.25,.5,.75):
                point = curve.Value(curve.FirstParameter()+f*(curve.LastParameter()-curve.FirstParameter()))
                require(point.X()>0 and point.Y()>0,"arc leaves first quadrant")
            arcs.append((center.Z(),circle.Radius()))
        else:
            require(curve.GetType()==GeomAbs_Line and ends in expected_lines,"wrong sector straight edge")
            expected_lines.remove(ends)
    require(not expected_lines and len(arcs)==2 and all(math.dist(a,b)<1e-8
            for a,b in zip(sorted(arcs),((0,10),(20,5)))),"lost or changed sector edge")
    volume,area = measure(shape,True),measure(shape,False)
    require(math.isclose(volume,875*math.pi/3,rel_tol=1e-9),"wrong sector volume")
    require(math.isclose(area,math.pi*(125+75*math.sqrt(17))/4+300,rel_tol=1e-9),"wrong sector area")
    return {"topology":counts,"volume_mm3":volume,"area_mm2":area,
            "angle_rad":math.pi/2,"quadrant":"positive_x_positive_y","arc_z_radius_mm":sorted(arcs),
            "straight_edge_count":7,"trim_membership_verified":True,"outward_normals_verified":True,
            "synthetic_seams":0,"brep_valid":True}


def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: check_cone_sector_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_cone_sector_shape(native),
                      "library_export":check_cone_sector_shape(exported),
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__=="__main__":
    main()
