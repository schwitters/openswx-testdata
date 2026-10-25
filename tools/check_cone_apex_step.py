#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Check original cone/apex and conical blind-drill fixtures in millimetres."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_Circle, GeomAbs_Cone, GeomAbs_Cylinder, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

from step_check import compare_solids, measure, read_step, require, topology_counts


def analytic(kind):
    if kind == "cone":
        return {"volume_mm3": 120 * math.pi,
                "area_mm2": math.pi * (36 + 6 * math.sqrt(136))}
    if kind == "blind-drill":
        return {"volume_mm3": math.pi * (6750 - 160 - 40 / 3),
                "area_mm2": math.pi * (900 + 225 + 209 + 80 + 4 * math.sqrt(22.25))}
    raise ValueError("Unknown apex fixture")


def check_shape(shape, kind):
    counts = topology_counts(shape)
    drill = kind == "blind-drill"
    require(counts["solids"] == 1 and counts["faces"] == (5 if drill else 2),
            "wrong complete apex solid")
    apex_z, slope = (17.5, 1.6) if drill else (10, -.6)
    normal_sign = -1 if drill else 1
    expected_rings = [(0, 15), (30, 15), (30, 4), (20, 4)] if drill else [(0, 6)]
    faces, edges, vertices = (TopTools_IndexedMapOfShape() for _ in range(3))
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    TopExp.MapShapes_s(shape, TopAbs_VERTEX, vertices)
    cones, cylinders, planes = 0, [], []
    for i in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        sign = 1 if face.Orientation() == TopAbs_FORWARD else -1
        if surface.GetType() == GeomAbs_Cone:
            cones += 1
            cone = surface.Cone()
            require(cone.Apex().Distance(gp_Pnt(0, 0, apex_z)) < 1e-8, "wrong apex position")
            require(abs(abs(cone.SemiAngle()) - math.atan(abs(slope))) < 1e-12,
                    "wrong cone half-angle")
            u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
            for fu in (.125, .375, .625, .875):
                for fv in (.25, .75):
                    u, v = u0 + fu * (u1 - u0), v0 + fv * (v1 - v0)
                    point = surface.Value(u, v)
                    x, y, z = point.X(), point.Y(), point.Z()
                    radius = math.hypot(x, y)
                    require(radius > 0 and abs(radius - slope * (z - apex_z)) < 1e-8,
                            "wrong complete cone profile or placement")
                    require((17.5 < z < 20) if drill else (0 < z < 10), "wrong cone trim")
                    require(BRepClass_FaceClassifier(face, point, 1e-8).State() == TopAbs_IN,
                            "cone sample outside the trimmed face")
                    props = BRepLProp_SLProps(surface, u, v, 1, 1e-10)
                    require(props.IsNormalDefined(), "undefined cone material normal")
                    n = props.Normal()
                    actual = [sign * n.X(), sign * n.Y(), sign * n.Z()]
                    scale = normal_sign / math.sqrt(1 + slope * slope)
                    expected = [scale * x / radius, scale * y / radius, -scale * slope]
                    require(math.dist(actual, expected) < 1e-10, "wrong cone material normal")
        elif surface.GetType() == GeomAbs_Cylinder:
            require(drill, "unexpected cylinder in a complete cone")
            cylinder = surface.Cylinder()
            radius = cylinder.Radius()
            require(any(abs(radius - r) < 1e-8 for r in (4, 15)), "wrong cylinder radius")
            require(math.hypot(cylinder.Location().X(), cylinder.Location().Y()) < 1e-8
                    and abs(abs(cylinder.Axis().Direction().Z()) - 1) < 1e-12,
                    "wrong cylinder axis or placement")
            u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
            u, v = .5 * (u0 + u1), .5 * (v0 + v1)
            p = surface.Value(u, v)
            require((20 < p.Z() < 30) if radius < 5 else (0 < p.Z() < 30), "wrong cylindrical trim")
            props = BRepLProp_SLProps(surface, u, v, 1, 1e-10)
            require(props.IsNormalDefined(), "undefined cylinder normal")
            n = props.Normal()
            outward = -1 if radius < 5 else 1
            require(math.dist([sign * n.X(), sign * n.Y(), sign * n.Z()],
                              [outward * p.X() / radius, outward * p.Y() / radius, 0]) < 1e-10,
                    "wrong bore/outer-cylinder material normal")
            cylinders.append(round(radius))
        else:
            require(surface.GetType() == GeomAbs_Plane, "unexpected apex-part support")
            plane = surface.Plane()
            z = plane.Location().Z()
            top = drill and abs(z - 30) < 1e-8
            require(top or abs(z) < 1e-8, "wrong cap level")
            require(abs(sign * plane.Axis().Direction().Z() - (1 if top else -1)) < 1e-12,
                    "wrong cap normal")
            require(BRepClass_FaceClassifier(face, gp_Pnt(0, 0, z), 1e-8).State()
                    == (TopAbs_OUT if top else TopAbs_IN), "lost drill opening or wrong cap")
            radius = 15 if drill else 6
            require(BRepClass_FaceClassifier(face, gp_Pnt(radius + 1, 0, z), 1e-8).State() == TopAbs_OUT,
                    "cap extends beyond the expected rim")
            planes.append(round(z))
    require(cones == 1 and sorted(cylinders) == ([4, 15] if drill else [])
            and sorted(planes) == ([0, 30] if drill else [0]), "wrong analytic face inventory")
    ring_turns = [0.] * len(expected_rings)
    poles = 0
    for i in range(1, edges.Extent() + 1):
        edge = TopoDS.Edge_s(edges.FindKey(i))
        if BRep_Tool.Degenerated_s(edge):
            points = TopTools_IndexedMapOfShape()
            TopExp.MapShapes_s(edge, TopAbs_VERTEX, points)
            require(points.Extent() == 1, "unexpected degenerate edge topology")
            p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(points.FindKey(1)))
            require(p.Distance(gp_Pnt(0, 0, apex_z)) < 1e-8, "pole edge away from the apex")
            poles += 1
            continue
        curve = BRepAdaptor_Curve(edge)
        if curve.GetType() == GeomAbs_Circle:
            circle = curve.Circle()
            require(math.hypot(circle.Location().X(), circle.Location().Y()) < 1e-8,
                    "eccentric apex-part ring")
            matches = [j for j, (z, r) in enumerate(expected_rings)
                       if abs(circle.Location().Z() - z) < 1e-8 and abs(circle.Radius() - r) < 1e-8]
            require(len(matches) == 1, "wrong ring level/radius")
            ring_turns[matches[0]] += curve.LastParameter() - curve.FirstParameter()
    require(poles == 1, "missing or duplicate reconstructed apex edge")
    require(all(abs(turn - 2 * math.pi) < 1e-8 for turn in ring_turns), "missing, duplicate or partial rim")
    require(any(BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(i))).Distance(gp_Pnt(0, 0, apex_z)) < 1e-8
                for i in range(1, vertices.Extent() + 1)), "lost apex vertex")
    expected = analytic(kind)
    actual = {"volume_mm3": measure(shape, True), "area_mm2": measure(shape, False)}
    require(all(math.isclose(actual[key], value, rel_tol=1e-9) for key, value in expected.items()),
            "wrong apex solid volume or area")
    return {"topology": counts, **actual, "apex_z_mm": apex_z, "cone_material_normals_verified": True,
            "reconstructed_pole_edges": poles, "brep_valid": True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("cone", "blind-drill"))
    parser.add_argument("native", type=Path)
    parser.add_argument("exported", type=Path)
    args = parser.parse_args()
    native, _ = read_step(args.native)
    exported, _ = read_step(args.exported)
    print(json.dumps({"ocp_distribution_version": importlib.metadata.version("cadquery-ocp"),
                      "native_reference": check_shape(native, args.kind),
                      "library_export": check_shape(exported, args.kind),
                      "bidirectional_difference_volume_mm3": compare_solids(native, exported)}, indent=2))


if __name__ == "__main__":
    main()
