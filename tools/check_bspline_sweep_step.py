#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Independent native STEP oracle for the original cubic-profile prisms."""
import argparse
import json
import math
import os
from pathlib import Path

from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.BRepClass import BRepClass_FaceClassifier
from OCP.BRepLProp import BRepLProp_SLProps
from OCP.BRepTools import BRepTools
from OCP.GeomAbs import GeomAbs_BSplineCurve, GeomAbs_BSplineSurface, GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_FORWARD, TopAbs_IN, TopAbs_OUT
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Pnt

from step_check import compare_solids, measure, read_step, require, topology_counts


def spec(name):
    if name == "cubic":
        return (0, 0, 0), 8, []
    if name == "multispan":
        return (20, -10, 5), 6, [(.3, 3), (.75, -2)]
    raise ValueError("Unknown cubic sweep fixture")


def profile(u, terms, derivative=0):
    factor = (1, 3, 6)[derivative]
    power = 3 - derivative
    return factor * (9 * u ** power + sum(c * max(u - k, 0) ** power for k, c in terms))


def integrate(function, start, end, tolerance=1e-11):
    """Independent adaptive Simpson length oracle; not exported geometry."""
    def recurse(a, b, fa, fm, fb, whole, eps, depth):
        m = (a + b) / 2
        fl, fr = function((a + m) / 2), function((m + b) / 2)
        left, right = (m - a) * (fa + 4 * fl + fm) / 6, (b - m) * (fm + 4 * fr + fb) / 6
        delta = left + right - whole
        if abs(delta) <= 15 * eps:
            return left + right + delta / 15
        require(depth > 0, "Length oracle failed to converge")
        return recurse(a, m, fa, fl, fm, left, eps / 2, depth - 1) + recurse(m, b, fm, fr, fb, right, eps / 2, depth - 1)
    fa, fm, fb = function(start), function((start + end) / 2), function(end)
    return recurse(start, end, fa, fm, fb, (end - start) * (fa + 4 * fm + fb) / 6, tolerance, 24)


def analytic(name):
    _, depth, terms = spec(name)
    height = profile(1, terms)
    section_area = 12 * (height - 9 / 4 - sum(c * (1 - k) ** 4 / 4 for k, c in terms))
    breaks = [0] + [k for k, _ in terms] + [1]
    length = sum(integrate(lambda u: math.hypot(12, profile(u, terms, 1)), a, b)
                 for a, b in zip(breaks, breaks[1:]))
    return {"volume_mm3": section_area * depth,
            "area_mm2": 2 * section_area + depth * (12 + height + length)}


def check_shape(shape, name):
    counts = topology_counts(shape)
    require(counts == {"faces": 5, "edges": 9, "vertices": 6, "solids": 1}, "Wrong complete prism topology")
    origin, depth, terms = spec(name)
    x0, y0, z0 = origin
    height = profile(1, terms)
    faces, edges = TopTools_IndexedMapOfShape(), TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    curved, planes, cap_levels = 0, [], []
    for i in range(1, faces.Extent() + 1):
        face = TopoDS.Face_s(faces.FindKey(i))
        surface = BRepAdaptor_Surface(face)
        sign = 1 if face.Orientation() == TopAbs_FORWARD else -1
        if surface.GetType() == GeomAbs_BSplineSurface:
            curved += 1
            spline = surface.BSpline()
            require((spline.UDegree(), spline.VDegree()) == (3, 1), "Wrong spline surface degrees")
            require(not spline.IsURational() and not spline.IsVRational(), "Unexpected rational sweep")
            u0, u1, v0, v1 = BRepTools.UVBounds_s(face)
            for fu in (.125, .375, .625, .875):
                for fv in (.25, .75):
                    u, v = u0 + fu * (u1 - u0), v0 + fv * (v1 - v0)
                    p = surface.Value(u, v)
                    t = (p.Y() - y0) / 12
                    require(0 < t < 1 and x0 - depth < p.X() < x0, "Wrong sweep position or trim")
                    require(abs(p.Z() - z0 - profile(t, terms)) < 1e-8, "Wrong cubic/truncated-power section")
                    props = BRepLProp_SLProps(surface, u, v, 1, 1e-10)
                    require(props.IsNormalDefined(), "Undefined swept material normal")
                    n = props.Normal()
                    derivative = profile(t, terms, 1)
                    norm = math.hypot(12, derivative)
                    require(math.dist([sign * n.X(), sign * n.Y(), sign * n.Z()],
                                      [0, derivative / norm, -12 / norm]) < 1e-10,
                            "Wrong swept material normal")
        else:
            require(surface.GetType() == GeomAbs_Plane, "Unexpected prism support")
            plane = surface.Plane()
            p, axis = plane.Location(), plane.Axis().Direction()
            normal = [sign * axis.X(), sign * axis.Y(), sign * axis.Z()]
            if abs(abs(normal[0]) - 1) < 1e-12:
                level = p.X()
                require(any(abs(level - x) < 1e-8 for x in (x0, x0 - depth)), "Wrong end-cap location")
                require(abs(normal[0] - (1 if abs(level - x0) < 1e-8 else -1)) < 1e-12, "Wrong end-cap normal")
                inside = gp_Pnt(level, y0 + 6, z0 + (profile(.5, terms) + height) / 2)
                outside = gp_Pnt(level, y0 + 6, z0 + profile(.5, terms) - .5)
                require(BRepClass_FaceClassifier(face, inside, 1e-8).State() == TopAbs_IN
                        and BRepClass_FaceClassifier(face, outside, 1e-8).State() == TopAbs_OUT,
                        "Wrong curved cap region")
                cap_levels.append(level)
                planes.append("cap")
            elif math.dist(normal, [0, -1, 0]) < 1e-12:
                require(abs(p.Y() - y0) < 1e-8, "Wrong left wall")
                planes.append("left")
            else:
                require(math.dist(normal, [0, 0, 1]) < 1e-12 and abs(p.Z() - z0 - height) < 1e-8,
                        "Wrong top wall")
                planes.append("top")
    require(curved == 1 and sorted(planes) == ["cap", "cap", "left", "top"], "Wrong face families")
    require(math.dist(sorted(cap_levels), [x0 - depth, x0]) < 1e-8, "Lost extrusion end")
    curved_edges = 0
    for i in range(1, edges.Extent() + 1):
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(i)))
        if curve.GetType() == GeomAbs_BSplineCurve:
            curved_edges += 1
            spline = curve.BSpline()
            require(spline.Degree() == 3 and not spline.IsRational(), "Wrong boundary spline")
            first, last = curve.FirstParameter(), curve.LastParameter()
            for f in (0, .1, .3, .5, .75, .9, 1):
                p = curve.Value(first + f * (last - first))
                t = (p.Y() - y0) / 12
                require(-1e-12 <= t <= 1 + 1e-12 and abs(p.Z() - z0 - profile(t, terms)) < 1e-8,
                        "Wrong boundary spline shape")
                require(any(abs(p.X() - x) < 1e-8 for x in (x0, x0 - depth)), "Wrong profile plane")
        else:
            require(curve.GetType() == GeomAbs_Line, "Unexpected prism edge")
    require(curved_edges == 2, "Lost original cubic profile boundaries")
    actual = {"volume_mm3": measure(shape, True), "area_mm2": measure(shape, False)}
    expected = analytic(name)
    require(all(math.isclose(actual[k], v, rel_tol=1e-9) for k, v in expected.items()), "Wrong exact prism measures")
    return {"topology": counts, **actual, "analytic": expected, "brep_valid": True,
            "cubic_profile_and_material_normals_verified": True, "spline_surface_degree": [3, 1]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=("cubic", "multispan"))
    parser.add_argument("step", type=Path)
    parser.add_argument("--reference", type=Path, default=os.environ.get("OPENSWX_CORPUS_BSPLINE_SWEEP_REFERENCE"), help="Independently captured native STEP for bidirectional solid differences")
    args = parser.parse_args()
    shape, _ = read_step(args.step)
    report = check_shape(shape, args.name)
    if args.reference:
        native, _ = read_step(args.reference)
        check_shape(native, args.name)
        report["bidirectional_difference_mm3"] = compare_solids(native, shape)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
