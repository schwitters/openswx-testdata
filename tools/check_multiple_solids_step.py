#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Verify each explicitly selected body against a two-body native STEP part."""
import importlib.metadata
import json
import sys
from pathlib import Path

from OCP.BRep import BRep_Builder
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.TopTools import TopTools_IndexedMapOfShape

from block_check import check_positioned_block
from step_check import compare_solids, read_step, require, topology_counts

SPECS = {"large-block": ((0,0,0),(20,30,40)),
         "small-block": ((50,0,0),(10,15,20))}


def check_selected_block(shape,key):
    return {"key":key,**check_positioned_block(shape,*SPECS[key])}


def native_bodies(shape):
    counts = topology_counts(shape)
    require(counts=={"faces":12,"edges":24,"vertices":16,"solids":2},
            "native reference must contain both disjoint blocks")
    solids = TopTools_IndexedMapOfShape()
    TopExp.MapShapes_s(shape,TopAbs_SOLID,solids)
    remaining = set(SPECS)
    matched = {}
    for i in range(1,solids.Extent()+1):
        solid = TopoDS.Solid_s(solids.FindKey(i))
        keys = []
        for key in remaining:
            try:
                check_selected_block(solid,key)
                keys.append(key)
            except RuntimeError:
                pass
        require(len(keys)==1,"wrong or duplicate native body ownership")
        key = keys[0]
        remaining.remove(key)
        matched[key] = solid
    require(not remaining,"missing native body")
    return matched


def check_multiple_solids(native,exports):
    require(set(exports)==set(SPECS),"both explicit body exports are required")
    bodies = native_bodies(native)
    reports = []
    builder,combined = BRep_Builder(),TopoDS_Compound()
    builder.MakeCompound(combined)
    for key in SPECS:
        exported = exports[key]
        report = check_selected_block(exported,key)
        report["bidirectional_difference_volume_mm3"] = compare_solids(bodies[key],exported)
        reports.append(report)
        builder.Add(combined,exported)
    return {"native_topology":topology_counts(native),"body_exports":reports,
            "combined_topology":topology_counts(combined),
            "bidirectional_difference_volume_mm3":compare_solids(native,combined)}


def main():
    if len(sys.argv)!=4:
        raise SystemExit("Usage: check_multiple_solids_step.py <native.step> <large.step> <small.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exports = {key:read_step(Path(path))[0] for key,path in zip(SPECS,sys.argv[2:])}
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      **check_multiple_solids(native,exports)},indent=2))


if __name__=="__main__":
    main()
