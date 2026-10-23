# Limits exposed by the first native cylinder capture

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
