# Limits exposed by the initial native captures

## Native Parasolid file envelope

`part-cylinder-001/reference/model.x_b` is a genuine SolidWorks binary export,
Parasolid 36.01.228, schema `SCH_3601228_36001`. It starts with an ASCII transmit
file header; the internal `PS\0\0` prologue is at byte 711.

The current libopenparasolid file reader expects `PS\0\0` at byte zero and
returns `unsupported_format` there. Preserve the original file unchanged. This
failure is checked separately from successful embedded binary-payload decoding.

A diagnostic transformation removes exactly the recorded 711-byte header and
stores the result as `derived/reference-without-ascii-header.x_b`. This decodes
completely, but its model report has ten unresolved references; it is not
accepted as a complete reference model. Both observations are frozen in the
case's provenance/validation records. Investigate standalone transmit context
and reference semantics with independent evidence before extending the reader.
Do not suppress missing-reference errors to turn this into a passing model.

The native `.x_t` is reference material. No text-grammar reader support is
claimed. The native AP214 STEP is independently imported by OCCT and used as the
geometric comparison oracle.

## Automatic history resolution

The saved `.sldprt` contains a partition and a delta payload in
`Contents/Config-0-Partition`. Both embedded payloads decode fully. The library
does not automatically reconstruct the active configuration state from them.

For this frozen fixture, the test explicitly selects extraction payload 0,
BODY 2. It verifies the complete selected body's geometry against native
SolidWorks observations and native STEP: a cylinder at the origin with radius
10 mm and height 20 mm. Native/reference STEP and exported checkpoint STEP have
zero bidirectional solid-difference volume in the recorded OCCT run.

This independently establishes the selected checkpoint's shape for this case;
it does not establish an automatic current-state selection algorithm or apply
the delta. The case contract and runner report retain that scope explicitly.

## Topology conventions

SolidWorks reports three faces, two closed edges, zero vertices and one
connected shell. XT records separate material-side and void-side shell uses;
the reader's body binding therefore reports two shells and six face uses.

The exporter adds one seam vertex to each otherwise vertex-free circle. OCCT
then adds an axial seam edge when reconstructing the periodic cylinder. The
imported native STEP and library STEP both have three faces, three edges and
two vertices. Compare these conventions explicitly rather than equating all
counts across APIs.

## Template provenance

Creation requested the backend's `configured_default` part template. The native
API observed an empty initial part, and later document/configuration custom
property queries returned no properties. Native feature history and source
preview were reviewed; the only modeled geometry is the generated cylinder.

The tools do not expose the resolved template file identity or its hash. That
field remains explicitly unavailable. The template file itself is not included
in the corpus. An explicit template identity/hash readback would improve future
capture reproducibility; it is separate from the cylinder's verified geometry.

## Block capture confirmation

`part-block-001` also contains a completely decoded embedded partition and delta,
and its standalone binary export also has an ASCII header ending at byte 711.
The block runner selects partition 0, BODY 2 explicitly and independently checks
its shape against native/reference geometry. No automatic history resolution is
claimed. Its six planar faces, twelve straight edges and eight named vertices
survive export/import without additional periodic seam topology.

## Tube capture confirmation

`part-tube-001` confirms the same embedded partition/delta and standalone binary
file-envelope distinction. Its explicit checkpoint export agrees with native
geometry and native/reference STEP, including the through bore and both annular
caps. OCCT adds two meridian seam edges as linear polynomial B-splines, absent
from the serialized source edges. Their topology and exact linear basis are
checked separately from the four original circular edges. No general spline
seam acceptance, geometry fitting or automatic history resolution is claimed.

## Blind-hole capture confirmation

`part-blind-hole-001` extends the native construction sequence with a real cut.
Its embedded partition and four-packet delta decode completely, and the explicit
checkpoint agrees with native/reference geometry, including the floor at Z=10 mm.
This adds a controlled subtractive-history example, without assigning unverified
operation meanings to delta status bytes or claiming automatic state recovery.
Its standalone native `.x_b` retains the ASCII-envelope limitation.

## Rectangular through-hole capture confirmation

`part-through-hole-001` uses a genuine through-all cut in rectangular stock.
Its embedded partition and four-packet delta decode completely. The explicit
checkpoint agrees with native/reference STEP, including circular holes in both
rectangular caps, eight preserved outer corners and the offset bore axis at
(10,15) mm. The shared seam checker uses that declared axis rather than assuming
the global origin. Standalone native `.x_b` envelopes and automatic history
resolution retain their previously documented limits.

## Stepped-bore capture confirmation

`part-stepped-bore-001` adds two ordered cuts, three cylindrical bands and an
internal annular shoulder. The partition and six-packet delta decode completely,
and the explicit checkpoint agrees with native/reference geometry and STEP.
Native standalone file envelopes and automatic state reconstruction retain the
same limits. Reopen provenance uses captured document handles verbatim; those
handles are opaque and must not be reconstructed from decimal counters.

## Repeated-bores capture confirmation

`part-two-holes-001` adds two disjoint circle profiles in one cut and three-loop
rectangular caps. Its partition and four-packet delta decode completely; the
explicit checkpoint agrees with native/reference geometry and STEP. Primitive
ownership is checked by geometric position, including equal-radius bores and
reversed construction order. Native file envelopes and automatic history
reconstruction retain their existing limits.

## Concave-profile capture confirmation

`part-concave-profile-001` adds one nonconvex outer cap wire and a reentrant
corner. Its partition and two-packet delta decode completely; the explicit
checkpoint matches native geometry and STEP. Supporting-plane samples outside
the cap trim are recorded and checked as outside. Native file envelopes and
automatic history reconstruction retain their existing limits.

## Multiple-solids capture confirmation

`part-multiple-solids-001` verifies two disjoint blocks in one native part. Both
explicit body selections pass topology, binding and individual STEP export; the
outputs agree separately and together with the whole native STEP reference. The
body mapping is reviewed by geometry, not inferred from enumeration order. The
export API still writes one selected body per call. Native file envelopes and
automatic history reconstruction retain their existing limits.

## Thin-wall capture confirmation

`part-thin-wall-001` preserves a 10-micrometre plate thickness, including both
cap planes, four short vertical edges and outward normals. Embedded streams
decode completely; the explicit checkpoint matches native geometry and STEP at
the unchanged 1e-8 m binding tolerance. This fixture does not establish a general
minimum feature size. Native file envelopes and automatic history resolution
retain their existing limits.

## Cone-frustum capture confirmation

`part-cone-frustum-001` adds a full revolution and a conical mantle. Embedded
payloads decode completely; the explicit checkpoint passes topology, binding
and STEP equivalence with native/reference geometry. Taper direction, material
normals and the straight periodic cone seam are checked independently. This is
one full, axis-aligned frustum. The subsequent sector capture below adds a
partial cone; oblique intersections remain planned. Native file envelopes and automatic history resolution retain their
existing limits.

## Cone-sector capture confirmation

`part-cone-sector-001` adds a 90-degree partial revolution, open circular arcs
and two radial cut faces. Both embedded payloads decode completely; the explicit
checkpoint matches native/reference geometry and STEP without synthetic seams.
Angular placement, arc intervals, trimmed-face membership and material normals
are checked independently. Other cone angles and oblique intersections are not
covered by this fixture. Native file envelopes and automatic history resolution
retain their existing limits.

## Boundary-free sphere STEP export

`part-sphere-001` contains one complete spherical face with no boundary loops,
edges or vertices. Extraction, complete binary decoding, topology and binding
pass. At library commit `1607ee9`, STEP export returns `unsupported_format` at
partition byte 2070: `STEP node 39: Face has no boundary loops`. No STEP output
is written. The corpus freezes this expected rejection and separately validates
the SolidWorks STEP reference, including the two natural poles and meridian seam
that OCCT constructs on import.

The exporter must support complete naturally closed surfaces before this can
become a passing STEP case. Keep geometry exact, account for degeneracies and
material orientation, and require independent native/library equivalence when
changing the expectation. Unexpected success is currently a regression requiring
review; a matched unsupported result is not counted as a passing STEP stage.
See the [sphere capture](sphere_capture.md) for the complete reproduction.

## OCCT sphere-cap reference projection

`part-sphere-cap-001` reveals a native-reference import defect in OCCT 7.9.3.1.1: the
exact rim circle receives an inaccurate sphere-side pcurve. Raw mass properties
miss the analytic cap values even though B-rep validity and the Boolean
difference test pass. The validator records those raw values, then rebuilds
only that reference pcurve on a deep copy using precise projection. It records
the achieved sampled correspondence and the adjusted import-only edge tolerance,
which must stay below the fixed source binding tolerance. Original STEP bytes,
3D rim/support geometry and the library output remain unchanged.

This reviewed oracle workaround is specific to the captured cap and its
one-circle native import; it does not mask library geometry failures. The
passing cap leaves the complete sphere's unsupported STEP expectation unchanged.
See [sphere-cap capture](sphere_cap_capture.md) for the full evidence, error
bounds and representation accounting.

## Boundary-free torus STEP export

`part-torus-001` is a complete R20/r5 mm ring torus, represented as one toroidal
face with no loops, edges or vertices. All five reader stages pass. At library
commit `1607ee9`, export rejects STEP node 39 with `unsupported_format` at
partition byte 2078: `Face has no boundary loops`. No STEP output is written.

The corpus freezes that rejection and independently verifies the native STEP's
two periodic circle seams and their common vertex. The torus has no pole
degeneracies. A future complete-surface export must preserve its central hole,
both periodic directions and material orientation. Unexpected success requires
review and independent equivalence before changing the expectation. See the
[torus capture](torus_capture.md).

## Meridional torus-cut STEP export

`part-torus-cut-001` is a valid 90-degree R20/r5 mm torus segment with two
meridional circle boundaries and planar end disks. All five reader stages pass.
At library commit `1607ee9`, export returns `invalid_record` at partition byte
2398: `STEP node 41: Torus cut circle is tilted or degenerate`. The current
`torus_boundary.cc` path handles circle normals aligned with the torus axis;
meridional cut normals are perpendicular and need a separate supported boundary
family. The error does not indicate malformed native input.

The corpus records outcome `unsupported` with the actual `invalid_record` API
code. It requires the exact rejection and no output, then validates the native
segment independently against analytic geometry. A future fix must preserve
both radial caps, angular trims and material orientation, and review the error
classification. See the [torus-segment capture](torus_cut_capture.md).

## Native rim-fillet capture confirmation

`part-fillet-001` generates an R2 mm top-rim blend on an R10/H20 mm cylinder
through the native SolidWorks fillet tool. It yields a regular torus band with
parallel circle cuts and passes topology, binding and STEP export. Native STEP,
library STEP and an independently kernel-built fillet agree geometrically, with
verified tangent joins, material normals and rational-seam bounds. This does
not cover arbitrary blends, boundary-free torus export or meridional torus cuts.
