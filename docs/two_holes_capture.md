# Captured two bores: part-two-holes-001

This original synthetic part was generated with SolidWorks 2025 SP5, revision
33.5.0, from a fresh empty part. Stock is a 40 x 30 x 20 mm block at the origin.
Two radius-3 mm bores at (10,15) and (30,15) mm pass through its Z thickness.
The configuration is `Default`.

The construction uses one rectangular base extrusion and one through-all cut
from a shared sketch containing two disjoint circles on the top XY plane.
Both profiles are retained in the declarative recipe. The source was saved,
closed, reopened and captured after another save. Geometry, configuration,
semantic revision and native update stamp were unchanged by reference export.
Only this run's documents were closed. Custom properties were empty; the
configured template file identity remains unavailable. Reopen handles are
recorded directly from native responses.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 70,271 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 8,103 | metre; 36.01.228 |
| Parasolid text | 8,714 | metre; 36.01.228 |
| STEP | 18,209 | millimetre; ISO-10303-21, AP214 |

All hashes agree with producer receipts. Native topology contains one solid,
eight faces, sixteen edges and eight corner vertices. Each Z cap has three
loops: one rectangular outer boundary and two circular inner boundaries. The
circular edges themselves are vertex-free in the source.

## Independent expectations

For block dimensions `w,d,h` and two equal bore radii `r`:

- Volume: `(w*d-2*pi*r^2)*h`.
- Boundary area: `2*(w*d+w*h+d*h)-4*pi*r^2+4*pi*r*h`.
- This case has volume `24000-360*pi` mm^3 and area `5200+204*pi` mm^2.
- Its centroid is (20,15,10) mm.

Both circles must have positive side clearance, and center distance must exceed
`2*r`. Tangent, overlapping and duplicate bores are rejected by recipe admission.
One hundred and twenty-six native curve/surface samples cover twelve lines,
four circles, six planes and two cylinders. Surface samples retain native trim
membership; bore mantle normals point into their own cavities.

## Reader and STEP evidence

The embedded partition contains 222 decoded nodes with no model/geometry issues:
twelve lines, four circles, six planes, two cylinders and eight point geometries.
The delta has two decoded nodes and four packets. Both payloads finish without
uninterpreted bytes. Explicit partition 0, BODY 2 passes topology and body
binding without interval overrides.

The exporter preserves eight faces and sixteen edges and adds four ring seam
vertices. OCCT reconstructs native and library STEP as valid B-reps with eight
faces, eighteen edges and twelve vertices, adding one axial seam per cylinder.
Both bores must retain full circular rims at Z=0 and Z=20 mm.

The checker maps each cylinder to its geometric center, then assigns its rims,
seam and seam vertices uniquely. Equal radii or enumeration order must not cause
one bore to stand in for the other. All eight stock corners, twelve stock edges,
six stock planes and both three-wire caps are verified. The two STEP solids have
zero bidirectional solid-difference volume.

Optional kernel tests accept reversed construction order and reject a missing
bore, one blind bore, and symmetric shifts of both bore centers. The shifted
pair retains volume, area and centroid, demonstrating why those scalars alone
cannot verify placement or contour ownership.

The [existing limits](known_limits.md) remain: explicit checkpoint verification
is not automatic history resolution, and standalone native `.x_b` ASCII headers
are not accepted directly by libopenparasolid.

## Repeat

Use the [shared starter runner](block_capture.md#repeat-an-admitted-starter-case)
with `--case part-two-holes-001` and a new output directory, for example:

```sh
.venv/bin/python tools/run_case.py \
  --case part-two-holes-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/two-holes-run-001
```
