# Captured native rim fillet: part-fillet-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, starts as a
radius-10 mm, height-20 mm cylinder at the origin along +Z. A native radius-2 mm
fillet rounds its top circular rim. Configuration is `Default`.

The cylinder is created by extruding an XY circle. A native B-rep query before
the fillet identifies the unique radius-10 mm circle centered at (0,0,20) mm.
Its actual owning EDGE reference is passed to a validated native `fillet`
feature, with tangent propagation disabled. The recipe stores a geometric rim
selector rather than an opaque runtime ID. Capture provenance retains the query
and exact reference used in the mutation.

The result has two planar faces, one cylinder and one torus. The cylindrical
wall ends at Z=18 mm. A regular torus with major radius 8 mm, minor radius 2 mm
and center (0,0,18) mm joins it tangentially to the radius-8 mm top disk at
Z=20 mm. The original radius-10 mm bottom disk remains at Z=0.

The configured-default part was empty and custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede
capture; native document handles are retained verbatim. Reference exports
preserved geometry, configuration, semantic revision and native update stamp.
Only this run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 119,777 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 4,370 | metre; 36.01.228 |
| Parasolid text | 4,709 | metre; 36.01.228 |
| Native STEP reference | 8,047 | millimetre; ISO-10303-21, AP214 |

All downloaded hashes and sizes match producer receipts. Source topology is one
solid, four faces, three vertex-free circular edges, zero vertices, six loops
and one connected shell. The circles have (Z,radius) pairs (0,10), (18,10) and
(20,8), in mm.

## Independent expectations

Let `R` be stock radius, `H` stock height, `f` fillet radius and `a=R-f`.
The initial recipe requires `f<H` and `2*f<R`, retaining a cylindrical wall and
a regular ring-torus support.

- Volume:
  `pi*(R^2*(H-f)+a^2*f+a*pi*f^2/2+2*f^3/3)`.
- Area:
  `pi*(R^2+a^2+2*R*(H-f)+2*f^2)+pi^2*a*f`.
- For this case, volume is `5800*pi/3+16*pi^2` mm^3, area is
  `532*pi+16*pi^2` mm^2, and centroid Z is
  `(56324+864*pi)/(5800+48*pi)` mm, approximately 9.9210814174 mm.
- Above Z=18 mm, the outer profile is
  `rho(z)=8+sqrt(4-(z-18)^2)`, in mm.
- The torus quarter profile satisfies `(rho-8)^2+(z-18)^2=4`, with
  `8<=rho<=10` and `18<=z<=20`, in mm.

Fifty-five native samples cover three circles (five each), two planes (five
each), the cylinder (five) and torus (twenty-five). They verify analytic
positions, trim membership and outward material normals. At the cylinder/torus
join, normals must agree with the cylinder's outward radial normal. At the
torus/top-disk join, normals must agree with +Z. The torus grid includes five
samples on each tangent join, including periodic U endpoints.

## Reader and STEP evidence

The 4,399-byte embedded partition decodes 110 nodes completely, with three
circles, one cylinder, two planes and one torus. There are no model/reference/
geometry issues. The 3,233-byte delta contains two ordinary schema nodes,
fifty delta nodes and four packets. Both streams finish without uninterpreted
bytes. Explicit partition 0, BODY 2 passes topology and geometry binding without
interval overrides.

STEP export succeeds. It preserves four faces and three edges and adds three
rim seam vertices. OCCT imports native and library STEP as valid single-solid
B-reps with four faces, five edges and three vertices: three circle rings, an
axial cylinder seam and a torus meridian seam. No reference-import repair is
required for this case.

The cylinder seam is a degree-one polynomial B-spline with two poles, certified
as straight, axial and periodic on the cylinder. The torus seam has an exact
constant-U pcurve and spans a quarter meridian from the cylinder join to the
top disk. OCCT represents its 3D curve as a positive-weight rational Bezier of
degree six with seven poles. A shared homogeneous Bernstein bound certifies
whole-curve radial error about the offset circle center. The observed bound is
approximately `2.692e-10` mm, below the imported edge tolerance and fixed source
binding tolerance of `1e-5` mm. Its control polygon must also remain in the
correct meridian plane and profile quadrant.

An independent `BRepFilletAPI` construction applies the same dimensional fillet
to a kernel-built cylinder. It uses an analytic-circle meridian; its pcurve is
a trimmed exact line, also accepted by the checker. Native STEP, library STEP
and the independent kernel reference all satisfy the measures, centroid, exact
surface families, three ring associations and material-normal checks. Both
native/kernel and native/library comparisons have zero bidirectional
solid-difference volume.

## Negative checks and scope

Kernel tests reject a bottom-rim fillet despite identical volume and area,
changed fillet radius, unfilleted stock, translation and inverted material
orientation. Rotation around the symmetry axis is accepted. Bezier tests also
verify the non-origin circle center and reject an interior control-point
excursion that leaves the endpoints unchanged.

This case proves native feature-based fillet capture and a successful toroidal
band export. Its cuts are parallel circles whose normals align with the torus
axis. It does not change the separate [meridional torus-cut limitation](known_limits.md#meridional-torus-cut-step-export), nor the full sphere/full torus
boundary-free export limitations. It is not coverage of arbitrary edge blends.
Standalone `.x_b` headers, `.x_t` text grammar and automatic history resolution
retain their [existing limits](known_limits.md).

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-fillet-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/fillet-run-001
```

The corpus contains fifteen complete passing export cases and three expected
export limitations.
