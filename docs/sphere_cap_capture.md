# Captured sphere cap: part-sphere-cap-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, is the upper
cap of a radius-10 mm sphere centered at the document origin. The cap is 5 mm
high, above the cutting plane Z=5 mm, with its north pole at Z=10 mm.
Configuration is `Default`.

A circular arc in the positive-X half of an explicit XZ plane runs from
(sqrt(75),5) to (0,10) mm. An axis-side segment and a radial base segment close
the profile, which is revolved through `2*pi` about +Z. The recipe's cap height
and radius must match the analytic dimensions. This initial contract supports
minor caps only: `0 < cap_height < radius`.

The part was created empty with a configured-default template and had no custom
properties. Template file identity remains unavailable. Save, close, reopen and
resave precede capture; actual document handles are retained. Reference exports
preserved geometry, configuration, semantic revision and native update stamp.
Only this run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 95,188 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 3,359 | metre; 36.01.228 |
| Parasolid text | 3,736 | metre; 36.01.228 |
| Native STEP reference | 5,293 | millimetre; ISO-10303-21, AP214 |

Downloaded hashes and sizes match producer receipts. Source topology is one
solid, two faces, one vertex-free circular edge, no vertices, two loops and one
connected shell. The spherical face and planar base share the same full circle.

## Independent expectations

For sphere radius `R` and cap height `h`:

- Base Z: `R-h`, here 5 mm.
- Rim radius: `sqrt(h*(2*R-h))`, here `sqrt(75)` mm.
- Volume: `pi*h^2*(R-h/3)`, here `625*pi/3` mm^3.
- Boundary area, including base: `pi*h*(4*R-h)`, here `175*pi` mm^2.
- Centroid Z: `3*(2*R-h)^2/(4*(3*R-h))`, here 6.75 mm.

Thirty native samples cover the circle (five), planar base (five) and spherical
surface (twenty). The spherical samples include the pole, rim and periodic
U boundaries. Sphere equations, Z limits, native trim membership, outward radius
normals and the downward base normal are checked independently.

## Reader and STEP evidence

The 3,344-byte embedded partition decodes 80 nodes completely, with one circle,
one plane and one sphere and no model/reference/geometry issues. The 724-byte
delta contains two ordinary schema nodes, two delta nodes and two packets. Both
streams finish without uninterpreted bytes. Explicit partition 0, BODY 2 passes
topology and geometry binding without interval overrides.

Unlike the [complete sphere](sphere_capture.md), this spherical face has a
boundary loop and exports successfully. The exporter preserves two faces and
one edge, adding one rim seam vertex. It writes exact `SPHERICAL_SURFACE` and
`CIRCLE` geometry.

OCCT imports the native STEP as two faces, one full-circle edge and one vertex.
The library STEP imports as two faces, four edges and three vertices: two rim
semicircles, one meridian seam and one degenerate north-pole edge. The checker
accounts for those representations explicitly, including complete nonoverlapping
rim coverage, natural pole ownership, trimmed-face membership and material
normals. Kernel-built positive tests also exercise one rim circle, an analytic
meridian and a degenerate pole edge.

### Importer-created meridian

The library STEP contains no polynomial spline approximation of the sphere.
OCCT generates a degree-six polynomial Bezier as the meridian's 3D curve during
import. Its pcurve on the sphere must be an exact constant-U line connecting the
rim and pole. The control polygon must stay in that meridian half-plane and the
cap's Z interval.

A Bernstein-product bound on `x(t)^2+y(t)^2+z(t)^2-100`, with a conservative
floating-point roundoff allowance, bounds radial error over the entire Bezier.
The observed bound is approximately `1.793e-6` mm, below both the imported edge
tolerance and the unchanged source binding tolerance, `1e-5` mm (`1e-8` m).
No arbitrary spline or endpoint-only approximation is accepted. An interior
control-point perturbation that leaves endpoints unchanged is rejected by the
bound test.

### Native reference projection workaround

OCCT 7.9.3.1.1 generates an inaccurate sphere-side pcurve for the native STEP's
exact rim circle. The raw imported B-rep reports valid topology but gives volume
654.4794085304 mm^3 and area 549.7552793907 mm^2, instead of 654.4984694979 mm^3
and 549.7787143782 mm^2. Sampled 3D/pcurve correspondence error reaches about
0.007375 mm, exceeding the imported edge tolerance of `1e-7` mm. A zero Boolean
difference alone does not expose this problem.

The validator records that raw import, then makes a deep B-rep copy. It rebuilds
only the faulty reference pcurve by projecting the unchanged exact 3D circle
onto the unchanged spherical support with `GeomProjLib`, requesting `1e-10` mm
precision. The measured maximum correspondence error over 1,025 parameter
samples drops to approximately `1.388e-7` mm. The copy's edge tolerance is set to
approximately `2.775e-7` mm, twice that measured error and still well below the
fixed `1e-5` mm source binding tolerance. The requested projection precision is
not represented as an achieved certified error bound.

Strict analytic measures and B-rep validity must then pass. Original and rebuilt
values, sample errors, requested precision and both edge tolerances are retained
under `native_reference_import` in `validation/occt.json`. The original import
and source STEP bytes remain unchanged. This workaround applies only to the
native reference and its reviewed one-circle topology; the library output never
receives this repair. Wrong source supports, rim dimensions or base placement
are rejected before rebuilding.

Both the original and corrected reference imports have zero bidirectional solid
difference volume against the library output. The corrected reference and the
unmodified library import also satisfy the independent volume/area formulas.
The raw import defect remains a separately documented
[oracle limitation](known_limits.md#occt-sphere-cap-reference-projection).

## Negative checks and scope

Kernel tests reject an opposite cap despite equal volume and area, changed cut
height, translation, wrong sphere radius, inward material orientation and a
missing planar base. They also verify that reference reprojection preserves the
original imported shape and stays within the fixed tolerance, and that the
Bezier bound detects an interior curve excursion.

The complete boundary-free sphere remains an expected unsupported library STEP
case. This passing cap does not change that expectation. Standalone native
`.x_b` headers, `.x_t` text grammar and automatic history resolution retain their
[existing limits](known_limits.md).

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-sphere-cap-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/sphere-cap-run-001
```
