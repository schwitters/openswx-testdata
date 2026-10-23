# Captured cone sector: part-cone-sector-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, is a 90-degree
sector of the R10/R5, 20 mm cone frustum. It occupies the positive-X, positive-Y
quadrant, from +X toward +Y around document +Z. Configuration is `Default`.

The same XZ trapezoid as the [full frustum](cone_frustum_capture.md) is revolved
through `pi/2` radians as a new body. The recipe now permits partial revolutions
about +Z through the origin. Its analytic angle must match the construction
angle; zero, negative and full-turn angles are rejected for a sector. The full
frustum still requires a full turn.

The configured-default part was empty and custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede
capture; actual document handles are retained from producer responses. Reference
exports preserved geometry, configuration, semantic revision and native update
stamp. Only this run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 90,612 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 5,884 | metre; 36.01.228 |
| Parasolid text | 6,497 | metre; 36.01.228 |
| STEP | 11,598 | millimetre; ISO-10303-21, AP214 |

Downloaded hashes and sizes match producer receipts. Source topology contains
one solid, five faces, nine edges, six vertices, five loops and one connected
shell. There is one conical mantle, two quarter-disk caps and two radial
trapezoidal cut faces.

## Independent expectations

For angle `a`, bottom radius `R`, top radius `r` and height `h`:

- Volume: `a*h*(R^2+R*r+r^2)/6`.
- Area: `a*(R^2+r^2+(R+r)*sqrt(h^2+(R-r)^2))/2 + (R+r)*h`.
- The last term is the area of both radial cuts; area is not simply a fraction
  of the full frustum's area.
- This 90-degree case has volume `875*pi/3` mm^3 and area
  `pi*(125+75*sqrt(17))/4 + 300` mm^2.
- Its centroid is `(75/(7*pi), 75/(7*pi), 55/7)` mm.
- The mantle follows `rho(z)=10-0.25*z`, in mm, only in the first quadrant.

The six vertices are the axis center and both arc endpoints at Z=0 and Z=20 mm.
Two holding circles retain their native closed/periodic metadata, but their
owning topological edges have distinct endpoints and span only `pi/2`. Seven
straight edges complete the radial caps, cut faces, axis and mantle generators.

Seventy-three native samples cover all nine curves (five each), four planes
(five each) and the cone (eight). Of the 28 surface samples, 24 are inside and
four outside their trimmed faces. Supporting-plane equations, arc intervals,
quadrant limits, radius law, cut normals and full cone material normals are
checked independently against positioned geometry.

## Reader and STEP evidence

The 5,931-byte embedded partition decodes 154 nodes completely. Typed geometry
contains two circles, one cone, seven lines, four planes and six points, with no
model/reference/geometry issues. The 1,020-byte delta contains two ordinary
schema nodes, two delta nodes and two packets. Both streams finish without
uninterpreted bytes. Explicit partition 0, BODY 2 passes topology and geometry
binding without interval overrides.

The exporter preserves all five faces, nine edges and six vertices. Both native
and library STEP import as valid single-solid B-reps with the same counts. No
synthetic periodic seam or synthetic vertex is required for this trimmed mantle.

The checker verifies positioned vertices, unique planar face boundaries,
conical radius law, supporting surface family, outward normals, seven exact
straight-edge endpoint pairs, two 90-degree arcs and the proper cap association.
It also tests interior and exterior points on all five trimmed supporting
surfaces. Trim classification uses analytic support parameters and the UV face
classifier: projecting an outside point onto a bounded patch can otherwise
snap it to the boundary. Native/reference and library solids have zero
bidirectional solid-difference volume.

Negative kernel tests reject a rotated sector and reversed taper despite equal
volume and area, a different angle with the same topology counts, a full
frustum, inverted material orientation and an equal-volume cylinder sector.
Measures and topology counts alone cannot certify angular placement, taper or
trimmed supporting-surface ownership.

The [existing limits](known_limits.md) remain: explicit checkpoint matching is
not automatic history reconstruction. Standalone native `.x_b` ASCII headers
and `.x_t` text grammar are not supported by the binary reader.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-cone-sector-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/cone-sector-run-001
```
