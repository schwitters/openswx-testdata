# Captured tube: part-tube-001

This original synthetic part was generated with SolidWorks 2025 SP5, revision
33.5.0, in a fresh empty part. Outer radius is 10 mm, inner radius 5 mm and
height 20 mm. The axis is +Z, the lower cap is at Z=0 and the configuration is
`Default`.

Two concentric circles belong to one XY sketch. A blind new-body extrusion
creates the through bore and both annular caps. The run saved, closed and
reopened the document, then saved/captured the reopened state. Geometry,
configuration, revision and native update stamp were unchanged by export.
Only documents created by this run were closed. Custom properties were empty;
the configured template's identity remains explicitly unavailable.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 97,193 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 4,558 | metre; 36.01.228 |
| Parasolid text | 4,851 | metre; 36.01.228 |
| STEP | 8,933 | millimetre; ISO-10303-21, AP214 |

All artifact hashes match the producer receipts. Native measurements report
one solid, four faces, four closed circular edges, zero vertices and one
connected shell. Volume is `1500*pi` mm^3 (about 4,712.38898038469 mm^3), and
boundary area is `750*pi` mm^2 (about 2,356.194490192345 mm^2).

Forty-six native samples cover all four circles, both planes and both cylinders.
They retain surface trim membership. Cylinder face normals point radially
outward on the outer mantle and inward into the bore on the inner mantle.

The saved source contains one partition and one delta payload. Both decode
completely with no uninterpreted bytes. The selected partition has 116 nodes,
including four circles, two cylinders and two planes, with no model/geometry
issues. Its explicitly selected BODY 2 passes topology and body binding without
interval overrides. This independently verified checkpoint is not an automatic
history/current-state reconstruction; the standalone native `.x_b` envelope
also retains the [known reader limitation](known_limits.md).

## STEP and periodic seams

The exporter preserves four faces and four circular edges and adds four
synthetic seam vertices to close the vertex-free rings. OCCT imports both the
native STEP and library STEP as valid solids with four faces, six edges and
four vertices. It adds one longitudinal periodic seam on each cylinder.

In this capture, those new seams are degree-one, two-pole, nonrational B-splines.
Neither original STEP file serializes a B-spline curve. The checker verifies
that each extra edge is a seam on a cylindrical face, its basis is an exact
line or a two-pole polynomial linear B-spline, its endpoints lie on the same
axial generator, and it spans both caps. One seam must lie at each radius.
The four original ring edges must remain exact circles with radii 5,5,10,10 mm.

Both planar caps must have two wires, preserving the inner hole. The independent
checks also verify concentric axes, radii, cap positions, analytic measures and
B-rep validity. Native/reference and library STEP have zero bidirectional
solid-difference volume in the recorded OCCT run.

## Repeat the checks

Use the [shared fixture runner](block_capture.md#repeat-an-admitted-starter-case),
setting `--case part-tube-001` and choosing a new output directory. For example:

```sh
.venv/bin/python tools/run_case.py \
  --case part-tube-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/tube-run-001
```

The corpus audit verifies frozen bytes and receipts separately from the six
library stages. Optional kernel tests additionally reject a filled bore,
a shifted tube, and an eccentric bore whose area and volume still match the
concentric reference. They run with:

```sh
/tmp/openswx-corpus-occt/bin/python -m unittest discover \
  -s tests -p test_step_checks.py -v
```
