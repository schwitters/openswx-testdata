# Captured elliptic extrusion: part-elliptic-profile-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, extrudes one
native XY ellipse along +Z through 20 mm. Semiaxes are 10 mm along X and 5 mm
along Y, centered at the origin. Configuration is `Default`. A fresh empty
configured-default part and empty custom properties were observed; template
file identity is unavailable. The native feature is an extrusion, not a
polygonal or spline approximation of an ellipse.

Save, close, reopen and resave precede capture. Original responses preserve
the actual native handles, configuration, revisions and update stamps.
Exports preserved document state; downloaded sizes and hashes match native
receipts. Only this run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 100,839 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 3,853 | metre; 36.01.228 |
| Parasolid text | 4,239 | metre; 36.01.228 |
| Native STEP reference | 10,323 | millimetre; ISO-10303-21, AP214 |

## Independent geometric expectations

For semiaxes `a>b>0` and height `h>0`, the volume is `pi*a*b*h` and area is
`2*pi*a*b+h*P`, where `P` is the complete ellipse perimeter. The offline
contract integrates `sqrt(a^2*sin(t)^2+b^2*cos(t)^2)` over a full turn, doubling
a periodic trapezoidal grid until successive results agree to `1e-13` relative.
It rejects nonconvergence and invalid dimensions. Recipes must match the
ellipse center, semiaxes, +Z direction and extrusion height.

This case has perimeter `48.44224110273838` mm, volume `1000*pi` mm^3,
area `1283.004087413747` mm^2 and exact centroid `(0,0,10)` mm. Every mantle
point satisfies `(x/10)^2+(y/5)^2=1` in mm. Outward material normals follow the
normalized gradient `(x/100,y/25,0)`; cap normals are -Z and +Z.

Seventy-three native evaluations cover two ellipse edges (nine each), two
planes (five each) and the mantle (forty-five). They verify analytic positions,
trim membership and material normals. The native B-rep API exposes the ellipse
curves exactly. Its mantle is native type 4009, reported as `other` with an
explicit unavailable exact descriptor. Direct native evaluation still succeeds;
no substituted surface descriptor is claimed.

## Native mass accuracy is a separate limitation

The native document mass API reports accuracy level 0; the body API uses its
default accuracy. Their preserved results are approximately:

- Volume `3142.35667763` mm^3, relative error `2.431964e-4`.
- Area `1283.23209603` mm^2, relative error `1.777146e-4`.
- Centroid displacement `0.516113` micrometre from the analytic centroid.

The MCP does not expose an accuracy selector. These values remain unchanged in
the native observations and saved source metadata. The fixture explicitly uses
`1e-3` relative allowance for native scalar admission, rather than treating the
mass values as exact. Saved metadata must still match those frozen observations
to `1e-9` relative in the runner. The source geometry/binding tolerance remains
`1e-8` m. Native centroid values are observations, not the analytic oracle.
The [precision report](../cases/part-elliptic-profile-001/validation/native-measure-precision.json)
records the errors and unavailable accuracy control.

## Reader and expected STEP rejection

The 3,864-byte embedded partition decodes all 96 nodes, including two ellipses,
two planes and one `swept_surface`. The 788-byte delta contains two ordinary
schema nodes, two delta nodes and two packets. Both streams finish without
uninterpreted bytes. Explicit payload 0, BODY 2 passes topology and geometry
binding without interval overrides. Native topology is one solid, three faces,
two vertex-free ellipse edges, zero vertices, four loops and one connected shell.

Library STEP export currently rejects the swept mantle with
`unsupported_format` at partition byte 2594:

```text
STEP node 41: Face export requires PLANE/CYLINDER/CONE/SPHERE or ring TORUS surfaces
```

The runner requires this exact frozen diagnostic, exit code 2 and no output
file. Unexpected success or a changed error requires review. This is a missing
supported face family; the source geometry is valid. There is no library STEP
output and no native/library STEP equivalence claim.

## Independent native STEP validation

OCCT imports the unmodified native STEP as a valid single solid with three
faces, three edges and two vertices. It represents the mantle as a rational
B-spline surface of degree 3 x 1, with 6 x 2 poles. The two V columns have
identical XY poles and weights and lie at Z=20 and Z=0 mm: the checker verifies
a straight, untapered extrusion over the full support domain.

Both ellipse boundaries and the mantle's cross section split into two rational
Bezier spans. Scaling Y by two maps the ellipse onto a radius-10 mm circle.
The shared homogeneous Bernstein bound certifies every span, with observed
scaled radial error at most `4.501e-10` mm. Positive weights and planarity are
required. Full-turn winding and perimeter checks guard against partial or
repeated contours. The imported axial seam is a straight degree-one polynomial
B-spline with two poles. Analytic cap trims, placement, seam endpoints and
material normals are checked separately.

OCCT's default surface/volume integration also loses accuracy on this rational
parameterization, even when asked for `1e-12` relative accuracy. Its reported
area `1283.00348407` mm^2 is retained for diagnosis. Volume uses span-aware
Gauss-Kronrod integration instead: `3141.592653589789` mm^3, estimated relative
error `2.202e-13`, with correct centroid. Boundary-derived area uses the
independently integrated edge perimeter plus the certified planar caps and
linear extrusion. The geometric checks retain fixed tolerances; the loose
native mass allowance is not passed to this oracle.

An independent OCCT construction extrudes an analytic ellipse. Both shapes
pass the geometry checks, and native/kernel bidirectional difference volumes
are zero. Negative tests reject swapped axes despite identical measures,
different semiaxes or a circular substitute with equal volume, wrong height,
translation, inverted orientation and an interior spline-pole excursion that
preserves endpoints. A symmetry half-turn is accepted.

## Scope and repeat

This fixture covers an exact axis-aligned elliptic extrusion and records its
[current exporter gap](known_limits.md#elliptic-sweep-step-export). It is not
a STEP export success or coverage of arbitrary spline surfaces. Native mass
precision, the unavailable native sweep descriptor, standalone binary headers,
text grammar and automatic delta/current-state resolution remain explicit limits.

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case):

```sh
.venv/bin/python tools/run_case.py \
  --case part-elliptic-profile-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/elliptic-profile-run-001
```
