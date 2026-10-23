# Captured cone frustum: part-cone-frustum-001

This first P1 capture is an original synthetic SolidWorks 2025 SP5 part,
revision 33.5.0, in configuration `Default`. Its bottom radius is 10 mm at Z=0,
top radius 5 mm at Z=20 mm, and height 20 mm. The axis is document +Z.

A trapezoid in the explicit XZ plane has sketch vertices, in mm:

```text
(0,0) -> (10,0) -> (5,20) -> (0,20) -> close
```

The plane normal is -Y and its local X axis is document +X, so sketch Y maps to
document +Z. A construction centerline from (0,-5) to (0,25) mm supplies the
rotation axis. A validated native `revolve` feature creates a new body through
`2*pi` radians. The recipe records the geometric axis separately from the
backend's sketch reference. Its initial revolution contract supports one XZ
polygon, a full rotation around +Z through the document origin and `new_body`.
The subsequent [sector capture](cone_sector_capture.md) extends the angle
contract to partial turns; other axes remain outside this recipe contract.

The configured-default part was empty and custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede capture;
actual native document handles are preserved in provenance. Reference exports
preserved geometry, configuration, semantic revision and native update stamp.
Only this capture's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 78,789 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 3,866 | metre; 36.01.228 |
| Parasolid text | 4,230 | metre; 36.01.228 |
| STEP | 6,655 | millimetre; ISO-10303-21, AP214 |

All downloaded sizes and hashes match producer receipts. The source has one
solid, three faces, two vertex-free circular edges, no vertices, four loops and
one connected shell: one periodic conical mantle and two planar disk caps.

## Independent expectations

For bottom radius `R`, top radius `r`, and height `h`, with `0<r<R`:

- Volume: `pi*h*(R^2+R*r+r^2)/3`, here `3500*pi/3` mm^3.
- Area: `pi*(R^2+r^2+(R+r)*sqrt(h^2+(R-r)^2))`, here
  `pi*(125+75*sqrt(17))` mm^2.
- Centroid Z: `h*(R^2+2*R*r+3*r^2)/(4*(R^2+R*r+r^2))`, here `55/7` mm.
- Mantle radius in document coordinates: `rho(z)=10-0.25*z`, in mm.
- Absolute cone half angle: `atan(0.25)` radians.

Twenty-eight native samples cover two circles (five each), two planes (five
each) and the cone (eight). Circle radii and cap associations, cap material
normals, cone radius law and full outward cone normals are checked. Every
surface sample is inside its native face trim.

The native cone reports positive half angle and axis +Z, while its recorded
trimmed V interval is [-0.02,0]. The physical radius decreases along document
+Z. The checker uses independently evaluated positions and normals, rather than
inferring the physical taper from the sign of the native parameter fields.

## Reader and STEP evidence

The 3,869-byte embedded partition decodes 95 nodes completely, with two circle,
one cone and two plane geometries and no model/reference/geometry issues. The
784-byte delta contains two ordinary schema nodes, two delta nodes and two
packets. Both payloads finish without uninterpreted bytes. Explicit partition
0, BODY 2 passes topology and geometry binding without interval overrides.

The exporter preserves three faces and two edges, adding one seam vertex to
each vertex-free ring. OCCT imports native and library STEP as valid B-reps
with three faces, three edges and two vertices, adding one generatrix seam.

The seam is verified as periodic on the cone, straight, spanning both rims and
remaining on one mantle generatrix. Native and library STEP represent it as a
nonrational degree-one B-spline with two poles. The independent kernel-built
positive test also exercises the analytic-line representation. Higher-degree
or otherwise uncertified spline seams are rejected, without approximation.

The checker also verifies cone axis and half angle, evaluated radius law,
outward material normals, full circular rims, uniquely associated cap radii,
cap trim membership and rim seam vertices. Native/reference and library solids
have zero bidirectional difference volume.

Negative kernel tests reject a reversed taper despite equal volume and area,
a translated frustum, wrong half angle, partial revolution, an equal-volume
cylinder and inverted material orientation. Exact scalar measurements alone do
not certify taper direction or the supporting surface family.

The [existing limits](known_limits.md) remain: explicit checkpoint verification
is not automatic history reconstruction. Standalone native `.x_b` ASCII headers
and `.x_t` text grammar are not supported by the binary reader.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-cone-frustum-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/cone-frustum-run-001
```
