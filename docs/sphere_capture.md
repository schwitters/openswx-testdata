# Captured sphere: part-sphere-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, is a complete
sphere of radius 10 mm centered at the document origin. Configuration is
`Default`. A right semicircle in an explicit XZ plane, closed by its diameter,
is revolved through `2*pi` about +Z to create a new body.

**Metadata, extraction, decoding, topology and binding pass. Library STEP export
is currently unsupported.** The native face has no boundary loops. The exporter
rejects that representation before writing a STEP artifact. This is a captured
regression and a known implementation gap, not a successful sphere export.

The configured-default part was empty and custom properties were empty. Template
file identity remains unavailable. Save, close, reopen and resave precede capture;
actual document handles are preserved. Reference exports preserved geometry,
configuration, semantic revision and native update stamp. Only this run's
documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 139,878 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 2,949 | metre; 36.01.228 |
| Parasolid text | 3,315 | metre; 36.01.228 |
| Native STEP reference | 3,938 | millimetre; ISO-10303-21, AP214 |

All downloaded hashes and sizes match producer receipts. Native topology is one
solid, one spherical face, one connected shell, zero edges, zero vertices and
zero loops. There is no missing extracted contour: this complete surface has
natural angular boundaries and needs no source trimming edges.

## Independent expectations

- Volume: `4*pi*10^3/3` mm^3.
- Area: `4*pi*10^2` mm^2.
- Centroid: (0,0,0) mm.
- Surface points satisfy `x^2+y^2+z^2=10^2`, in mm.
- Outward material normals equal the normalized radius vectors.

Twenty-five native surface samples cover U=0, pi/2, pi, 3*pi/2 and 2*pi, crossed
with V=-pi/2, -pi/4, 0, pi/4 and pi/2. The ten pole samples must collapse to the
same two antipodal physical locations for every U. The samples at U=0 and 2*pi
must coincide. Native trim membership, sphere equations and normals are checked
at regular points, seam boundaries and poles. Pole positions belong to the
native support frame; sphere orientation is geometrically arbitrary.

The recipe uses an explicit `sketch_semicircle` primitive in the positive-X half
of the XZ plane. Its radius must match the analytic sphere radius and its
revolution must be complete. Other half planes or partial spheres require a
contract extension.

## Reader and native STEP evidence

The 2,816-byte embedded partition decodes 65 nodes and one typed sphere, without
model/reference/geometry issues. The 664-byte delta has two ordinary schema
nodes, two delta nodes and two packets. Both streams finish without
uninterpreted bytes. Explicit partition 0, BODY 2 passes topology and geometry
binding with the original boundary-free face and no interval overrides.

SolidWorks' STEP contains an `ADVANCED_FACE` with no bounds on a
`SPHERICAL_SURFACE`. OCCT imports it as a valid complete single-solid B-rep with
one face, three edges and two vertices: two degenerate pole edges and one exact
semicircular meridian seam. The support's pole axis in this reference is +Y;
it is not the document +Z revolution axis. The checker therefore verifies poles
relative to the imported sphere's own frame.

The independent checker verifies the complete spherical UV domain, exact center
and radius, outward normals, both distinct poles, degenerate-edge ownership and
the periodic meridian connecting the poles. A separately kernel-constructed
analytic sphere has zero bidirectional difference volume against the native
reference. This comparison validates the native oracle; it is not a comparison
to a library-produced STEP file.

## Exact expected library failure

At library commit `1607ee9a22b1aba7e2a6607061c209845d591dd0`, the typed export
result is:

```json
{
  "error_code": "unsupported_format",
  "offset": 2070,
  "message": "STEP node 39: Face has no boundary loops"
}
```

The offset is relative to the selected embedded partition. The source face is
node 39. `BodyWriter::PrepareFaces` currently rejects empty boundary-loop lists.
Supporting the natural sphere requires explicit treatment of a complete closed
surface, including its pole/seam representation and material orientation.

`validation/export-error.json` retains the API fields. The test driver emits
structured JSON failures while preserving diagnostic stderr and exit code 2.
Its body-ID parser also rejects values outside the uint32 node-ID range before
conversion. The runner checks the exact error code, offset and message and
requires no STEP output. Unexpected success, a partial output file, changed
error fields or an unrelated failure fail the regression and require review.
The run report records `step: unsupported` and
`step_equivalence: not_tested_no_library_output`.

Optional kernel tests accept another pole-axis orientation, and reject a wrong
radius, translated sphere, hemisphere and inward material orientation.

The [other known limits](known_limits.md) remain: standalone native `.x_b` ASCII
headers, `.x_t` text grammar and automatic delta/current-state reconstruction
are not supported by this replay.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case) with the
updated `case_export` driver and a new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-sphere-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/sphere-run-001
```

Exit zero means all declared expectations matched, including the known export
rejection. It does not mean the STEP stage passed. Thirteen captured cases have
complete passing STEP regressions; the full torus and meridionally trimmed
torus segment are two further expected export limitations.
