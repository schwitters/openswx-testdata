# Captured torus segment: part-torus-cut-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, is a
90-degree segment of an R20/r5 mm ring torus. It runs from +X toward +Y around
document +Z and occupies the positive-X, positive-Y quadrant. The torus support
is centered at the origin. Configuration is `Default`.

An XZ circle of radius 5 mm at (20,0) mm is revolved through `pi/2` as a new
body. This creates one toroidal mantle and two planar meridional end disks.
It satisfies the planned trimmed-torus case without a separate subtractive cut.
The recipe's partial rotation angle, circle radius and radial offset must match
its independent analytic dimensions. Full turns are rejected for this case.

**Metadata, extraction, decoding, topology and binding pass. STEP export is
currently unsupported by the exporter.** The actual API rejection is
`invalid_record`, not `unsupported_format`. The native input is valid; the
exporter currently rejects this boundary family. The corpus records both that
implementation limitation and the actual error classification without rewriting
it into a different error code.

The configured-default part was empty and custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede capture;
actual document handles are retained. Reference exports preserved geometry,
configuration, semantic revision and native update stamp. Only this run's
documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 120,011 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 3,854 | metre; 36.01.228 |
| Parasolid text | 4,264 | metre; 36.01.228 |
| Native STEP reference | 6,677 | millimetre; ISO-10303-21, AP214 |

All downloaded hashes and sizes match producer receipts. Source topology is one
solid, three faces, two vertex-free circle edges, zero vertices, four loops and
one connected shell. The two cut circles have radius 5 mm and centers (20,0,0)
and (0,20,0) mm. Their planes are Y=0 and X=0, respectively. Outward cut normals
are -Y and -X.

## Independent expectations

For partial angle `a`, major radius `R` and minor radius `r`, with `0<r<R`:

- Volume: `a*pi*R*r^2`, here `250*pi^2` mm^3.
- Boundary area: `2*a*pi*R*r + 2*pi*r^2`, here `100*pi^2+50*pi` mm^2.
- The final area term accounts for both end disks.
- Centroid for this quarter segment: `(40.625/pi,40.625/pi,0)` mm.
- Mantle equation: `(sqrt(x^2+y^2)-20)^2+z^2=25`, restricted to the first quadrant.

Forty-five native samples cover both cut circles (five each), both planar caps
(five each) and the torus (twenty-five). The torus holding surface remains
periodic in U and V, but the face's trimmed U span is only `pi/2`; V spans a
complete `2*pi`. Native trim membership, positions, inner/outer torus normals
and the two distinct cut-face material normals are verified independently.

## Reader and native STEP evidence

The 3,865-byte embedded partition decodes 95 nodes completely, with two circles,
two planes and one torus and no model/reference/geometry issues. The 784-byte
delta contains two ordinary schema nodes, two delta nodes and two packets. Both
streams finish without uninterpreted bytes. Explicit partition 0, BODY 2 passes
topology and geometry binding without interval overrides.

OCCT imports the native STEP as a valid solid with three faces, three edges and
two vertices. The two source meridional circles are retained. A parallel seam
joins the two rim vertices, closing the periodic tube direction. There are no
pole degeneracies. The checker verifies each circle's unique end-disk ownership,
full circular interval, center, radius and plane; it also verifies the clipped
mantle, outward normals and end-disk trim membership.

The imported torus uses an unwrapped U chart, approximately [5*pi/2,3*pi].
Physical inside/outside probes are mapped to the corresponding periodic UV
chart before classification. Treating the canonical U returned by a surface
parameter calculation as an absolute trimmed-domain coordinate would be wrong.

### Exact pcurve and rational seam bound

The seam has an exact constant-V torus pcurve spanning `pi/2` in U. Its imported
3D representation is a positive-weight rational Bezier of degree six with seven
poles, lying in Z=-5 mm on a parallel circle of radius 20 mm. A kernel-built
positive test also exercises an analytic-circle seam on a different parallel.

The shared Bezier helper bounds the homogeneous Bernstein polynomial
`||H(t)||^2-radius^2*W(t)^2`, then uses the positive lower bound on `W(t)` to bound
radial error over the whole curve. A conservative floating-point allowance is
included. The observed radial bound is approximately `2.53e-11` mm, below the
imported edge tolerance and fixed source binding tolerance of `1e-5` mm. The
same helper also covers the polynomial meridian in the sphere-cap check.

Uniform weight scaling leaves the accepted geometry unchanged. Corrupting an
interior weight while retaining the endpoint weights is detected by the bound;
zero or negative weights are rejected. Control poles must remain in the correct
first-quadrant parallel plane. Endpoint checks alone cannot certify this seam.

An independent kernel-built quarter torus has zero bidirectional solid-difference
volume against the native reference. Analytic volume and area also agree. No
reference projection workaround is needed here. No library STEP was produced,
so this comparison validates only the native oracle.

## Exact expected library failure

At library commit `1607ee9a22b1aba7e2a6607061c209845d591dd0`, export returns:

```json
{
  "error_code": "invalid_record",
  "offset": 2398,
  "message": "STEP node 41: Torus cut circle is tilted or degenerate"
}
```

The offset is relative to the selected embedded partition. In
`torus_boundary.cc`, the current boundary path requires circle normals aligned
with the torus axis: parallel cuts through the tube profile. This segment's
valid meridional circles have normals perpendicular to the torus axis and are
therefore rejected. Supporting this case requires an additional boundary family,
not a relaxed alignment tolerance. The API's `invalid_record` classification for
this valid unsupported case also deserves review when implementing support.

`validation/export-error.json` retains the typed rejection. The runner requires
the same code, offset and message and no STEP artifact. Unexpected success or a
changed failure requires review. The report uses corpus outcome
`step: unsupported`, actual error code `invalid_record`, and
`step_equivalence: not_tested_no_library_output`.

Kernel tests reject changed radii, translation, wrong axis, wrong quadrant,
changed partial angle, inward material orientation and a full torus. Rotated
quadrants retain volume and area, so those scalars alone do not certify angular
placement. The full sphere and full torus retain their separate boundary-free
[export limitations](known_limits.md).

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-torus-cut-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/torus-cut-run-001
```

Exit zero means the declared expectations matched, including this exact
rejection. It is not a passing STEP export. The corpus contains fourteen
complete passing export cases and three expected export limitations.
