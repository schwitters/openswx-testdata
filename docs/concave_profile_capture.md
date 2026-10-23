# Captured L-profile: part-concave-profile-001

This original synthetic part was generated in a fresh empty SolidWorks 2025 SP5
part, revision 33.5.0, using configuration `Default`. Its XY outline, in mm, is:

```text
(0,0) -> (40,0) -> (40,10) -> (15,10) -> (15,30) -> (0,30) -> close
```

A single six-line sketch is extruded 20 mm along +Z. The reentrant corner is
(15,10) mm. The outline is one concave outer wire; there is no inner hole.
The source was saved, closed, reopened and saved with artifact capture. Reference
exports preserved geometry, configuration, semantic revision and native update
stamp. Only documents created by this capture were closed. Configured-default
template identity remains unavailable; the new part was empty and custom
properties were empty. Raw producer responses retain the actual reopen handles.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 62,085 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 8,413 | metre; 36.01.228 |
| Parasolid text | 9,163 | metre; 36.01.228 |
| STEP | 18,083 | millimetre; ISO-10303-21, AP214 |

All downloaded sizes and hashes match producer receipts. Source topology is one
solid, eight planar faces, eighteen straight edges and twelve vertices, with one
connected shell and eight loops. Both caps have one six-edge outer wire.

## Independent expectations

Let `w,d,h` be overall dimensions, `a` the vertical leg width, and `b` the
horizontal leg depth. Require `0<a<w` and `0<b<d`:

- Section area: `S=w*b+a*(d-b)`.
- Volume: `S*h`, here 14,000 mm^3.
- Boundary area: `2*S+2*(w+d)*h`, here 4,200 mm^2.
- Centroid: (14.642857142857143, 11.428571428571429, 10) mm.

The polygon recipe uses an implicit closing edge. Duplicate vertices,
self-intersections, contact between nonadjacent edges and zero area are rejected.
Both winding directions are accepted.

Native evaluation retains 138 samples: five per straight edge, five per
rectangular side face, and a nine-point UV grid on each concave cap. Of 48
surface samples, 40 lie within the trimmed faces and eight lie in the removed
rectangle. The latter are valid points on the supporting plane and must be
classified outside the trimmed face. Each cap independently contains five inside
and four outside samples. Plane equations, curve parameters, material normals
and the profile's occupied region are checked against analytic expectations.

## Reader and STEP evidence

The 8,514-byte embedded partition decodes 232 nodes completely, with eighteen
line, eight plane and twelve point geometries. The 1,332-byte delta decodes two
nodes and two packets completely. No bytes remain uninterpreted. Explicit
partition 0, BODY 2 passes topology and geometry binding without interval
overrides. Geometry-model and reference checks report no issues.

The exporter preserves eight faces, eighteen edges and twelve vertices. No
synthetic seam geometry is needed. OCCT imports both reference and library STEP
as valid single-solid B-reps with those same counts. The checker independently
verifies all vertex positions, edge endpoint pairs, face boundaries, outward
normals and the cap trim classification in both legs and the notch. Bidirectional
solid-difference volumes are zero.

Optional kernel tests accept reversed winding and a different starting vertex.
They reject a mirrored notch despite identical volume and surface area, a filled
notch, and inverted material orientation. Scalar measures alone do not certify
concavity, trim membership or material orientation.

The [existing limits](known_limits.md) still apply: explicit checkpoint matching
is not automatic history reconstruction. Native standalone `.x_b` ASCII headers
and `.x_t` text grammar are not supported by the binary reader.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-concave-profile-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/concave-profile-run-001
```
