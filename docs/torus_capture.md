# Captured torus: part-torus-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, is a regular
ring torus centered at the document origin, with major radius 20 mm, minor
radius 5 mm and symmetry axis document Z. Configuration is `Default`.

A circle of radius 5 mm at (20,0) mm in an explicit XZ plane is revolved through
`2*pi` around document +Z. The recipe records the radial offset separately from
the profile radius. Both must match the analytic major/minor radii. Only regular
ring tori are admitted: `0 < minor_radius < major_radius`. Horn and spindle tori
are outside this recipe contract.

**Metadata, extraction, decoding, topology and binding pass. Library STEP export
is currently unsupported.** Like the [complete sphere](sphere_capture.md), the
torus is represented by one complete face without boundary loops. The exporter
rejects it before producing a STEP file.

The configured-default part was empty and custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede
capture; actual document handles are retained from producer responses. Reference
exports preserved geometry, configuration, semantic revision and native update
stamp. Only this run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 140,962 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 2,955 | metre; 36.01.228 |
| Parasolid text | 3,315 | metre; 36.01.228 |
| Native STEP reference | 3,961 | millimetre; ISO-10303-21, AP214 |

All downloaded sizes and hashes match producer receipts. Source topology is one
solid, one toroidal face, one connected shell, zero loops, zero edges and zero
vertices. The surface is periodic and closed in both parameter directions.

## Independent expectations

For major radius `R=20` mm and minor radius `r=5` mm:

- Volume: `2*pi^2*R*r^2`, here `1000*pi^2` mm^3.
- Area: `4*pi^2*R*r`, here `400*pi^2` mm^2.
- Centroid: (0,0,0) mm.
- Surface equation: `(sqrt(x^2+y^2)-R)^2+z^2=r^2`.
- Inner/outer equator radii: 15 and 25 mm; tube Z extrema: -5 and +5 mm.
- Outward material normal: `((rho-R)*x/(r*rho), (rho-R)*y/(r*rho), z/r)`.

Twenty-five native samples cross U=0, pi/2, pi, 3*pi/2, 2*pi with
V=-pi, -pi/2, 0, pi/2, pi. Both pairs of periodic boundary rows must coincide.
Positions satisfy the analytic torus equation. Inner-side normals point radially
toward the central hole, while outer-side normals point away from the axis.
Every sample retains native face trim membership.

## Reader and native STEP evidence

The 2,822-byte embedded partition decodes 65 nodes completely, with one typed
torus and no model/reference/geometry issues. The 664-byte delta has two ordinary
schema nodes, two delta nodes and two packets. Both streams finish without
uninterpreted bytes. Explicit partition 0, BODY 2 passes topology and geometry
binding with its original boundary-free face and no interval overrides.

SolidWorks STEP contains a complete toroidal face without explicit bounds.
OCCT imports it as a valid single-solid B-rep with one face, two exact circular
seam edges and one shared seam vertex. One seam follows a meridian (radius
5 mm); the other follows a parallel (radius 25 mm in this reference). Both are
periodic on the same face. There are no degenerate pole edges.

The checker verifies the surface family, center, axis, both radii, full UV
periods, material normals and the two independent seam directions. Both seam
circles must close on the shared vertex at the natural surface-domain corner.
An independent kernel-built torus has zero bidirectional solid-difference
volume against the native reference. This validates the native oracle; no
library-produced STEP is available for comparison.

Seam positions belong to the support parameterization, not the physical ring
geometry. A shifted full tube period can place the parallel seam on the inner
15-mm equator. Such parameterizations and rotations about the symmetry axis are
accepted. Translation, a changed symmetry axis, changed major/minor radii,
partial major rotation and inward material orientation are rejected.

## Exact expected library failure

At library commit `1607ee9a22b1aba7e2a6607061c209845d591dd0`, export returns:

```json
{
  "error_code": "unsupported_format",
  "offset": 2078,
  "message": "STEP node 39: Face has no boundary loops"
}
```

The offset is relative to the selected embedded partition. The face is node 39.
`BodyWriter::PrepareFaces` currently rejects empty loop lists. Supporting a
complete torus requires treatment of a naturally closed, doubly periodic
surface. It must preserve the central hole and both seam directions; sphere
pole degeneracies must not be copied into the torus representation.

The corpus freezes this exact typed error in `validation/export-error.json`.
The shared runner requires the same code, offset and message and no STEP
artifact, and separately validates the native STEP reference. Unexpected
success, a partial output or a changed failure requires review. Exit zero means
the expectations matched; the report still records `step: unsupported` and
`step_equivalence: not_tested_no_library_output`.

Standalone native `.x_b` ASCII headers, `.x_t` text grammar and automatic
history reconstruction retain their [existing limits](known_limits.md).

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case) and a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-torus-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/torus-run-001
```

The corpus contains fourteen complete passing export cases. The complete
sphere, complete torus and meridionally trimmed torus segment have expected
export limitations.
