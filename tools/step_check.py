# SPDX-License-Identifier: MIT
# Copyright (c) 2026 openswx contributors
"""Shared OCCT import, validity and solid-difference checks for corpus fixtures."""
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_Reader
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_VERTEX, TopAbs_SOLID
from OCP.TopExp import TopExp
from OCP.TopTools import TopTools_IndexedMapOfShape


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def measure(shape, volume):
    if shape.IsNull():
        return 0.0
    properties = GProp_GProps()
    operation = BRepGProp.VolumeProperties_s if volume else BRepGProp.SurfaceProperties_s
    operation(shape, properties, Eps=1e-12)
    return properties.Mass()


def topology_counts(shape):
    require(not shape.IsNull() and BRepCheck_Analyzer(shape).IsValid(), "invalid B-rep")
    counts = {}
    for name, kind in (("faces", TopAbs_FACE), ("edges", TopAbs_EDGE),
                       ("vertices", TopAbs_VERTEX), ("solids", TopAbs_SOLID)):
        entities = TopTools_IndexedMapOfShape()
        TopExp.MapShapes_s(shape, kind, entities)
        counts[name] = entities.Extent()
    return counts


def read_step(path):
    reader = STEPControl_Reader()
    require(reader.ReadFile(str(path)) == IFSelect_RetDone, f"cannot read {path}")
    reader.SetSystemLengthUnit(1.0)  # OCCT STEP output coordinates in millimetres.
    require(reader.TransferRoots() == 1, "expected exactly one STEP root")
    shape = reader.OneShape()
    return shape, topology_counts(shape)


def compare_solids(native, exported):
    differences = []
    for first, second in ((native, exported), (exported, native)):
        cut = BRepAlgoAPI_Cut(first, second)
        require(cut.IsDone(), "geometric difference operation failed")
        remainder = abs(measure(cut.Shape(), True))
        require(remainder < 1e-6, "solid difference exceeds 1e-6 mm^3")
        differences.append(remainder)
    return differences
