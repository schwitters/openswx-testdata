#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Check the exact bounds and material orientation of a 10 micrometre plate."""
import importlib.metadata
import json
import math
import sys
from pathlib import Path

from block_check import check_positioned_block
from step_check import compare_solids, read_step, require

DIMENSIONS_MM = (20,30,.01)
BINDING_TOLERANCE_M = 1e-8


def check_thin_wall_shape(shape):
    report = check_positioned_block(shape,(0,0,0),DIMENSIONS_MM)
    minimum_feature_m = min(DIMENSIONS_MM)*.001
    require(math.isclose(report["volume_mm3"],6,rel_tol=1e-9),"wrong thin-wall volume")
    require(math.isclose(report["area_mm2"],1201,rel_tol=1e-9),"wrong thin-wall area")
    return {**report,"minimum_feature_size_m":minimum_feature_m,
            "binding_tolerance_m":BINDING_TOLERANCE_M,
            "feature_to_tolerance_ratio":minimum_feature_m/BINDING_TOLERANCE_M,
            "outward_material_normals_verified":True}


def main():
    if len(sys.argv)!=3:
        raise SystemExit("Usage: check_thin_wall_step.py <native.step> <exported.step>")
    native,_ = read_step(Path(sys.argv[1]))
    exported,_ = read_step(Path(sys.argv[2]))
    print(json.dumps({"ocp_distribution_version":importlib.metadata.version("cadquery-ocp"),
                      "native_reference":check_thin_wall_shape(native),
                      "library_export":check_thin_wall_shape(exported),
                      "bidirectional_difference_volume_mm3":compare_solids(native,exported)},indent=2))


if __name__=="__main__":
    main()
