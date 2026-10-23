# Captured exact rim chamfer: part-chamfer-001

This original synthetic SolidWorks 2025 SP5 part (33.5.0), configuration
`Default`, is an R10/H20 mm cylinder with a C2 x 45-degree top-rim chamfer.
The captured MCP catalogue has no native Chamfer feature. A native full
revolution constructs the exact geometry from the XZ polygon
`(0,0),(10,0),(10,18),(8,20),(0,20)` mm about document +Z through the origin.
This tests chamfer geometry, not a native Chamfer feature or its history.

The four faces are two disks, the remaining cylindrical wall at Z=0..18 mm,
and a conical band at Z=18..20 mm with `rho(z)=28-z` mm. The top disk radius
is 8 mm; the bottom remains 10 mm. The three circles have (Z,radius) pairs
`(0,10),(18,10),(20,8)` mm. Material normals change sharply at both band joins.
The [fillet case](fillet_capture.md) shares these ring positions and topology,
but has a torus band and tangent joins instead.

The configured-default part was empty; custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede
capture. Provenance preserves actual native handles, validation and execution
readbacks, unchanged export state, receipts and download hashes. Only this
run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 91,040 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 4,388 | metre; 36.01.228 |
| Parasolid text | 4,770 | metre; 36.01.228 |
| Native STEP reference | 8,063 | millimetre; ISO-10303-21, AP214 |

## Independent expectations

For stock radius `R`, height `H`, chamfer size `c`, let `r=R-c`.
The recipe requires `0<c<R` and `c<H`.

- Volume: `pi*(R^2*(H-c)+c*(R^2+R*r+r^2)/3)`.
- Area: `pi*(R^2+r^2+2*R*(H-c)+(R+r)*sqrt(2)*c)`.
- This case has volume `5888*pi/3` mm^3 and area
  `(524+36*sqrt(2))*pi` mm^2, approximately 6165.89918145 mm^3 and
  1806.13833625 mm^2. Centroid is `(0,0,57836/5888)` mm.
- The conical material normal is `(x/rho,y/rho,1)/sqrt(2)`.

Fifty-five native evaluations check three circles (five each), two planes
(five each), the cylinder (five), and cone (twenty-five). They verify positions,
trim membership and material normals. Five cone samples on each ring verify
the normal discontinuity against the neighboring cylinder or top disk.
Native support parameter signs are not physical taper directions: the saved
cone has a positive half-angle, but its radius decreases with document Z.

## Reader and STEP evidence

The 4,409-byte embedded partition completely decodes 110 nodes, including
three circles, two planes, one cylinder and one cone. The 844-byte delta
contains two ordinary schema nodes, two delta nodes and two packets. Both
streams decode without uninterpreted bytes. Explicit payload 0, BODY 2 passes
topology and geometry binding without interval overrides.

Native topology is one solid, four faces, three vertex-free circular edges,
zero vertices, six loops and one connected shell. STEP export preserves the
four faces and three rings and introduces three seam vertices. OCCT imports
both native and library STEP as valid single solids with four faces, five
edges and three vertices, adding cylinder and cone generator seams.

Both imported seams are degree-one non-rational B-splines with two poles.
The cylinder seam is axial. The cone generator joins the rings at the same
azimuth and has an exact constant-U support pcurve. The checker certifies its
straight 3D representation, endpoints and support correspondence. No reference
repair is needed.

An independent `BRepFilletAPI_MakeChamfer` applies C2 to a kernel-built
cylinder's top rim. Its seams are analytic lines. Native STEP, library STEP
and this independently constructed chamfer satisfy topology, support families,
ring associations, outward normals, volume, area and centroid checks.
Native/kernel and native/library bidirectional difference volumes are zero.

Kernel tests reject the opposite rim despite identical measures, wrong size,
unchamfered stock, translation, inverted material orientation and a fillet
substitute with the same topology and ring positions. Rotation about +Z is
accepted. Contract tests reject inconsistent profiles and partial revolutions.

## Scope and repeat

This is one exact equal-distance circular-rim chamfer. It does not cover native
Chamfer feature semantics, unequal distances or arbitrary edge networks.
Standalone binary headers, text parsing and automatic current-state/delta
resolution retain their [existing limits](known_limits.md). The selected
embedded checkpoint is independently shape-verified.

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case):

```sh
.venv/bin/python tools/run_case.py \
  --case part-chamfer-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/chamfer-run-001
```
