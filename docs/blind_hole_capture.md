# Captured blind hole: part-blind-hole-001

This original synthetic part was constructed with SolidWorks 2025 SP5, revision
33.5.0, from an empty part. Stock is a cylinder of radius 10 mm and height 20 mm.
A concentric radius-5 mm bore enters at Z=20 mm and ends on a flat floor at
Z=10 mm. The configuration is `Default`.

The recipe creates a base extrusion followed by an actual subtractive extrusion.
The top sketch uses an explicit XY plane at Z=20 mm; the cut direction reverses
its +Z support normal. The source was saved, closed, reopened and captured after
saving the reopened state. Geometry, configuration, semantic revision and native
update stamp were unchanged by reference export. Only this run's documents were
closed. Custom properties were empty; the template file identity is unavailable.

One rebuild request was rejected as busy with `outcome_unknown: false`; the
identical request and operation ID succeeded on retry. Both responses remain in
the capture journal. No uncertain native outcome was retried.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 99,504 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 4,858 | metre; 36.01.228 |
| Parasolid text | 5,194 | metre; 36.01.228 |
| STEP | 9,406 | millimetre; ISO-10303-21, AP214 |

All downloaded hashes match the producer receipts. Native topology has one
solid, five faces, four vertex-free circular edges and one connected shell.
The five faces are the outer mantle, blind-bore mantle, external bottom disk,
internal floor disk and annular top face.

## Independent expectations

For stock radius `R`, bore radius `r`, stock height `H` and bore depth `d`:

- Volume: `pi*R^2*H - pi*r^2*d`.
- Boundary area: `2*pi*R^2 + 2*pi*R*H + 2*pi*r*d`; the removed top disk and
  added bore floor have equal areas.
- This case therefore has volume `1750*pi` mm^3 and area `700*pi` mm^2.
- Its centroid is `(0,0,65/7)` mm. The stock center is at Z=10 mm and the
  removed volume's center at Z=15 mm.

Fifty-one native curve/surface samples verify all four circular rings, three
planes and two cylinders, including surface trim membership. The inner mantle
exists only above the floor. Native normals point into the bore on that mantle,
upward on the internal floor/top face and downward on the external bottom.

The recipe contract now supports a cut after an existing solid extrusion and
negative-Z extrusion direction. A cut before a solid, a bore as wide as the
stock, or a depth consuming the entire floor is rejected. Other construction
operations remain outside this starter recipe language.

## Reader and STEP evidence

The embedded partition has 125 decoded nodes, including four circles, two
cylinders and three planes, with no model/geometry issues. The delta stream has
two decoded nodes and four packets. Both payloads decode completely without
uninterpreted bytes. The explicit checkpoint selection is partition 0, BODY 2;
recorded topology and body binding succeed without interval overrides.

The checkpoint exports as one solid with five faces, four circular edges and
four synthetic ring vertices. OCCT adds two longitudinal seams and reconstructs
both native and library STEP as valid B-reps with five faces, six edges and four
vertices. The outer seam spans Z=0..20 mm; the inner seam spans Z=10..20 mm.
Both seams are checked as exact axial lines, including their degree-one,
two-pole polynomial B-spline representation when introduced by OCCT.

The oracle checks the cap wire inventory `(Z, wires) = (0,1),(10,1),(20,2)` and
ring locations `(radius,Z) = (5,10),(5,20),(10,0),(10,20)` in millimetres. These
checks distinguish top entry from bottom entry, which can have the same volume
and area. Analytic measures and zero bidirectional solid-difference volume
independently confirm the native/reference and exported shapes agree.

The [existing limits](known_limits.md) remain: explicit checkpoint verification
is not automatic delta/current-state reconstruction, and standalone native
`.x_b` ASCII envelopes are not accepted directly by the reader.

## Repeat

Use the [shared starter runner](block_capture.md#repeat-an-admitted-starter-case)
with `--case part-blind-hole-001`. Choose a new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-blind-hole-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/blind-hole-run-001
```

Optional OCCT tests reject wrong entry side, wrong depth, a through hole and an
eccentric bore. Wrong-entry and eccentric cases explicitly retain the original
volume/area and must still fail geometric verification.
