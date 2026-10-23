#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify the native/exported 20 x 30 x 40 mm block, including exact placement."""
import importlib.metadata
import itertools
import json
import math
import sys
from pathlib import Path

from OCP.BRep import BRep_Tool
from OCP.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Line, GeomAbs_Plane
from OCP.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_VERTEX
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS
from OCP.TopTools import TopTools_IndexedMapOfShape

from step_check import compare_solids, measure, read_step, require, topology_counts


def check_block_shape(shape):
    counts = topology_counts(shape)
    require(counts == {"faces": 6, "edges": 12, "vertices": 8, "solids": 1},
            "incomplete block topology")
    vertices = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_VERTEX, vertices)
    unmatched = set(itertools.product((0,20), (0,30), (0,40)))
    for index in range(1, vertices.Extent()+1):
        point = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertices.FindKey(index)))
        actual = (point.X(), point.Y(), point.Z())
        matches = [p for p in unmatched if math.dist(actual, p) < 1e-8]
        require(len(matches) == 1, "wrong block dimension or placement")
        unmatched.remove(matches[0])
    faces, edges = TopTools_IndexedMapOfShape(), TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape, TopAbs_FACE, faces)
    TopExp.MapShapes_s(shape, TopAbs_EDGE, edges)
    for index in range(1, faces.Extent()+1):
        surface = BRepAdaptor_Surface(TopoDS.Face_s(faces.FindKey(index)))
        require(surface.GetType() == GeomAbs_Plane, "nonplanar block face")
    for index in range(1, edges.Extent()+1):
        curve = BRepAdaptor_Curve(TopoDS.Edge_s(edges.FindKey(index)))
        require(curve.GetType() == GeomAbs_Line, "nonlinear block edge")
    volume, area = measure(shape, True), measure(shape, False)
    require(math.isclose(volume, 24000, rel_tol=1e-9), "wrong block volume")
    require(math.isclose(area, 5200, rel_tol=1e-9), "wrong block boundary area")
    return {"topology": counts, "volume_mm3": volume, "area_mm2": area,
            "bounds_mm": [[0,0,0],[20,30,40]], "brep_valid": True}


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: check_block_step.py <native.step> <exported.step>")
    native, _ = read_step(Path(sys.argv[1]))
    exported, _ = read_step(Path(sys.argv[2]))
    native_report, exported_report = check_block_shape(native), check_block_shape(exported)
    differences = compare_solids(native, exported)
    print(json.dumps({"ocp_distribution_version": importlib.metadata.version("cadquery-ocp"),
                      "native_reference": native_report, "library_export": exported_report,
                      "bidirectional_difference_volume_mm3": differences}, indent=2))


if __name__ == "__main__":
    main()
