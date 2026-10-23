# Captured stepped bore: part-stepped-bore-001

This original synthetic part was generated with SolidWorks 2025 SP5, revision
33.5.0, in a fresh empty part. Stock is a cylinder of radius 10 mm and height
20 mm. A radius-3 mm through bore is enlarged to radius 6 mm for the upper 8 mm,
leaving an annular shoulder at Z=12 mm. The configuration is `Default`.

The recipe uses a base extrusion and two separate subtractive features: a
through-all cut followed by a blind counterbore, both from the upper XY plane
in direction -Z. Native measurements were recorded before and after each cut.
The document was saved, closed, reopened and captured after a further save.
Reference exports did not alter geometry, configuration, semantic revision or
native update stamp. Only this run's documents were closed. Custom properties
were empty; the configured template file identity remains unavailable.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 104,369 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 5,574 | metre; 36.01.228 |
| Parasolid text | 5,934 | metre; 36.01.228 |
| STEP | 11,744 | millimetre; ISO-10303-21, AP214 |

All hashes match producer receipts. Native topology has one solid, six faces,
six vertex-free circular edges and one connected shell. Its faces are three
cylinders and three planar annuli: bottom, top and internal shoulder.

## Analytic reference

For stock radius `R`, through-bore radius `r`, counterbore radius `s`, stock
height `H` and counterbore depth `d`:

- Volume: `pi*((R^2-r^2)*H - (s^2-r^2)*d)`.
- Boundary area: `2*pi*(R^2-r^2) + 2*pi*(R*H + r*(H-d) + s*d)`.
- Radii must satisfy `0 < r < s < R`, and depth `0 < d < H`.

This case has volume `1604*pi` mm^3 and area `750*pi` mm^2. Its centroid is
`(0,0,14744/1604)` mm. The stock's volume is `2000*pi`, the through cut removes
`180*pi` at Z=10 mm and the additional counterbore removes `216*pi` at Z=16 mm.

Sixty-nine native samples verify all circles, planes and cylinders, including
surface trim membership. The small bore exists at Z=0..12 mm, the larger bore
at Z=12..20 mm. Both internal mantles have inward radial material normals;
the shoulder and top face point upward and the bottom face downward.

## Reader and STEP evidence

The embedded partition has 146 decoded nodes, with six circles, three cylinders
and three planes, and no model/geometry issues. The delta contains two decoded
nodes and six packets. Both payloads finish without uninterpreted bytes.
Explicit partition 0, BODY 2 passes topology and body binding without overrides.
This is independently verified checkpoint selection, not automatic history
reconstruction.

The exporter retains six faces and six circular edges and adds six ring seam
vertices. OCCT reconstructs both STEP files as valid B-reps with six faces,
nine edges and six vertices. The oracle checks annular planes at Z=0,12,20 mm,
all six circle radius/height pairs, and axial seam spans R3/Z0..12,
R6/Z12..20 and R10/Z0..20 mm. Importer-created linear B-spline seams use the
existing exact straight-seam certificate.

The native and exported STEP agree with the analytic measures and have zero
bidirectional solid-difference volume. Negative kernel tests reject a reversed
counterbore entry, wrong depth, missing shoulder and eccentric enlargement.
Reversed-entry and eccentric examples retain the correct volume and area.

## Replay and provenance

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case) with
`--case part-stepped-bore-001`, the existing `case_export` executable and a new
report directory. The [known reader limits](known_limits.md) remain explicit.

Document handles are opaque strings. This capture's derived reopen summary
uses values from actual native responses (`doc-b` to `doc-c`), rather than
formatting a decimal counter. The previous through-hole capture had a wrong
human-written summary (`doc-10` instead of actual `doc-a`). Its derived summary
has been corrected and rehashed, with a correction note; raw events, native
CAD/reference files and measurements are unchanged. A regression test compares
both structured summaries against their captured open responses.
