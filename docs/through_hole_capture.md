# Captured through hole: part-through-hole-001

This original synthetic part was generated with SolidWorks 2025 SP5, revision
33.5.0, from an empty part. Stock dimensions are 20 x 30 x 40 mm along X/Y/Z,
with lower corner at the origin. A radius-5 mm bore lies at X=10, Y=15 mm and
opens through both Z caps. The configuration is `Default`.

The native sequence creates a rectangular base extrusion, then a separate
circular sketch on an explicit plane at Z=40 mm. An actual `through_all` cut
uses the reversed support normal (-Z). No cut depth was requested. The recipe
schema now represents this mode explicitly and forbids a competing depth or an
unbounded new-body boss. The native extrusion's auxiliary depth readback is not
used to infer through-cut extent; native geometry and the STEP oracle verify it.

The source was saved, closed, reopened and saved/captured again. Geometry,
configuration, revision and native update stamp were unchanged by export.
Only this run's documents were closed. Custom properties were empty; the
configured template's identity remains unavailable.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 70,657 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 7,395 | metre; 36.01.228 |
| Parasolid text | 7,944 | metre; 36.01.228 |
| STEP | 15,873 | millimetre; ISO-10303-21, AP214 |

All artifact hashes match their native receipts. Native topology has one solid,
seven faces, fourteen edges and eight outer corner vertices. The two circular
bore rims are vertex-free in the source. One hundred and eight native samples
verify twelve line curves, two circles, six planes and one cylinder, including
surface trim membership and outward material normals. The bore mantle's normals
point toward its axis.

## Analytic reference

For block width `w`, depth `d`, height `h` and bore radius `r`:

- Volume: `w*d*h - pi*r^2*h`.
- Boundary area: `2*(w*d+w*h+d*h) - 2*pi*r^2 + 2*pi*r*h`.
- This case has volume `24000-1000*pi` mm^3 and area `5200+350*pi` mm^2.
- The centered bore leaves the centroid at (10,15,20) mm.

The bore must have positive clearance from every block side. A tangent or
side-breaking circle is outside this closed-hole construction subset. Metadata
regression now compares the saved centroid with native measurements as well as
volume and area.

## Reader and STEP evidence

The embedded partition has 201 decoded nodes and no model/geometry issues.
Its typed geometry contains twelve lines, two circles, six planes, one cylinder
and eight points. The delta has two decoded nodes and four packets. Both payloads
finish without uninterpreted bytes. Explicit partition 0, BODY 2 passes recorded
topology and complete body binding without interval overrides.

The checkpoint exports seven faces, fourteen edges and ten vertices, adding
one seam vertex to each circular rim. OCCT adds one axial seam and reconstructs
both native and library STEP with seven faces, fifteen edges and ten vertices.
The imported seam is checked as an exact line or two-pole polynomial linear
B-spline on the cylindrical face, relative to the offset axis at (10,15) mm;
its Z span must be 0..40 mm.

The oracle retains all eight stock corners, twelve straight stock edges and
two complete circular rims. It verifies all six block support planes, with two
wires on each Z cap and one on every side face. The bore radius, axis, position,
cap openings, analytic measures and B-rep validity must agree. Native/reference
and exported STEP have zero bidirectional solid-difference volume.

The [known limits](known_limits.md) still apply: checkpoint selection is explicit,
not automatic history recovery, and the reader does not directly accept the
standalone native `.x_b` ASCII envelope.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case):

```sh
.venv/bin/python tools/run_case.py \
  --case part-through-hole-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/through-hole-run-001
```

Optional OCCT tests reject a missing bore, a blind bore and a shifted bore whose
volume and area match the centered reference. Recipe tests verify clear side
walls and an unambiguous through-all mode. Frozen native samples and artifact
hashes are checked separately from library execution.
