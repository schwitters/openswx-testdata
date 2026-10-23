# Library regression contract

The repository includes an offline integrity/admission validator and a working
six-stage runner for the captured cylinder, block, tube, blind hole, through hole, stepped bore, two bores, a concave L-profile, two separated solids, a thin wall, a cone frustum, a cone sector, a full sphere, a minor spherical cap, a ring torus, a quarter-torus segment, a native rim fillet, an exact revolved chamfer and an elliptic extrusion. See the
[cylinder](cylinder_capture.md), [block](block_capture.md), [tube](tube_capture.md)
[blind-hole](blind_hole_capture.md), [through-hole](through_hole_capture.md),
[stepped-bore](stepped_bore_capture.md), [two-bores](two_holes_capture.md) and
[concave L-profile](concave_profile_capture.md),
[multiple solids](multiple_solids_capture.md),
[thin wall](thin_wall_capture.md), [cone frustum](cone_frustum_capture.md) and
[cone sector](cone_sector_capture.md), [sphere](sphere_capture.md) and
[sphere cap](sphere_cap_capture.md), [torus](torus_capture.md) and
[torus segment](torus_cut_capture.md), [native fillet](fillet_capture.md), [exact chamfer](chamfer_capture.md) and [elliptic extrusion](elliptic_profile_capture.md) captures for native evidence, commands and exact checkpoint scope. Other cases
remain planned. No library result is inferred from a manifest.

## Independent stages

| Stage | Input and checks | Success evidence |
| --- | --- | --- |
| Metadata | Native document through libopenswx | Correct document kind, available properties/configurations/references against native observations |
| Extraction | libopenswx payload inventory | Complete observed inventory, kind/configuration associations, captured sizes and reviewed extraction hashes |
| Decode | Each explicitly selected binary payload through libopenparasolid | Complete supported wire decoding, or an exact expected error with diagnostic offset |
| Topology | Explicit body in a complete selected state | Owned reference graph and recorded incidence validated |
| Binding | Body curves/surfaces/trims and explicit units/tolerances | Supported geometry binds; native samples and relevant domains agree |
| STEP | Selected body through libopenswstep | Complete body exported, OCCT-valid B-rep and semantic agreement with native/reference geometry |

Use the existing C++ public APIs for missing CLI output, rather than scraping
human-readable logs. Keep SolidWorks and OCCT dependencies outside library cores.
Native text Parasolid exports are reference material: libopenparasolid currently
reads binary streams, so `.x_t` must not be counted as a passing text decode.

A native Parasolid reference and an embedded payload need not be byte-identical.
Do not infer the current model from the first embedded partition or from stream
order. Select configuration, state and body explicitly; unresolved history is a
separate unsupported outcome, not an invitation to select an old snapshot.

## Expected outcomes

Each case declares `pass`, `unsupported` or `not_applicable` for each stage.
Unsupported expectations need an issue identifier and exact error code.
`not_applicable` needs a reason. Expectations are reviewed contracts, not observed
results. Record observations in an independent run report with:

- Corpus Git commit, library Git commit, runner version and platform.
- Case ID, selected configuration, payload/state/body identity and source unit.
- Per-stage observed outcome, expected outcome and match/mismatch.
- Error code, byte offset/entity and resource profile where applicable.
- Measured/expected quantities, tolerances and diagnostics/artifact paths.

A blocked downstream stage is recorded as blocked and never counted as passing.
Unexpected success of a known-unsupported case prompts review; the runner must
not silently rewrite the expectation. Changed unsupported codes also fail the
contract. Report counts separately per stage and document/body occurrence.

## STEP oracle

Import the SolidWorks reference STEP and the library-produced STEP with a pinned
OCCT/OCP environment. The existing openswx roundtrip harness uses OCP 7.x; reuse
its compatible validation environment initially and record the actual version.

Require non-null complete output, B-rep validity and the intended body kinds.
Compare analytic measures where available and native volume, area, centroid,
placement and selected geometric distances. Add bidirectional geometric checks
for trims/surfaces as coverage grows; finite samples do not prove global shape
equivalence. Correct area and volume alone do not establish a correct model.

Account explicitly for importer-created periodic seams and topology splits.
Distinguish preserved source-edge topology from imported topology. Reparameterized
curves need geometry-based correspondence; matching numeric parameters or IDs
without proven correspondence is invalid. Missing source faces/bodies are errors,
not acceptable partial exports. Keep ordinary source tolerances separate from
larger, explicitly declared tolerant-edge allowances.

## CI rollout

1. Preparation CI: validate plan, recipes and captured artifact integrity; run
   contract tests. An empty corpus is reported honestly.
2. After the first admission: enable `--require-ready`, run a pinned small corpus
   against the libraries and OCCT. Fail if required selected cases are absent.
3. PR tests: a stable curated fast subset. Nightly: all admitted cases plus
   sanitizers and bounded resource/error regressions.
4. Separate Windows regeneration jobs: check semantic reproduction with explicit
   producer builds. Never overwrite reference fixtures automatically.

Deterministic malformed-input cases should derive from an original admitted
fixture with a named mutation, seed, parent hash and expected diagnostic. They
must not be confused with genuine SolidWorks output or silently broaden the
valid corpus. Preserve the existing hand-built unit fixtures for packet layouts,
exact budget boundaries and geometries the producer does not emit.

## Multiple-body selections

`part-multiple-solids-001` records document measurements separately from its two
native bodies. `selection.bodies` maps each explicit XT BODY ID to one native
body key, with unique IDs and complete native-key coverage. The runner checks
both bodies before passing topology or binding, exports each one separately and
compares each output to its positioned native STEP solid. It also compares the
combined outputs to the entire native reference. Selecting a non-BODY node must
fail without producing a STEP file. See the [capture](multiple_solids_capture.md).

## Small feature preservation

`part-thin-wall-001` is a 20 x 30 x 0.01 mm plate. Its 10-micrometre thickness
is recorded explicitly, at 1,000 times the unchanged 1e-8 m binding tolerance.
The independent checker preserves distinct cap planes, four short vertical edges
and eight positioned vertices. It rejects micrometre-scale thickness and
placement changes, collapsed geometry and wrong material orientation. This is a
resolved fixture, not a certified lower bound for supported feature sizes.

## Conical geometry

`part-cone-frustum-001` adds a full native revolution with a conical supporting
surface. Its independent checker verifies the radius law along document Z, cap
radii, material normals and an importer-created generatrix seam. Seam acceptance
requires a true straight periodic seam on the cone, represented as a line or a
nonrational degree-one B-spline with two poles. Equal volume and area do not
permit a reversed taper to pass. See the [capture](cone_frustum_capture.md).

## Partial revolutions and arc trims

`part-cone-sector-001` verifies a 90-degree first-quadrant frustum sector. It
retains two open circular arcs, seven lines, six vertices and two outward radial
cut faces. Interior/exterior support probes are classified directly in UV,
without projecting outside points onto a bounded patch. Native holding-circle
periodicity must not override a topological edge's partial parameter interval.
The recipe's construction angle and analytic angle must agree. See the
[capture](cone_sector_capture.md).

## Expected boundary-free sphere rejection

`part-sphere-001` currently passes metadata, extraction, decode, topology and
binding. Its STEP expectation is `unsupported_format` at partition byte 2070,
with the exact node-39 missing-loops diagnostic in `validation/export-error.json`.
The export driver exposes typed error fields as JSON. The runner requires the
exact frozen error and no STEP output, then validates only the native spherical
STEP oracle. Unexpected success or a changed failure requires review. Exit zero
means expectations matched; the report still records STEP as `unsupported`, not
`pass`, and library/native STEP equivalence as untested.

## Spherical-cap oracle and importer seams

`part-sphere-cap-001` exports successfully. Native and library STEP have
different imported seam/pole topology, which the checker accounts for explicitly.
An importer-created polynomial meridian requires an exact spherical pcurve and
a whole-curve Bernstein radial bound within the fixed length tolerance.

The native reference's default OCCT pcurve projection is inaccurate. The checker
records raw geometry checks and measured disagreement, then reprojects only that
pcurve on a deep copy. Corrected measures, retained source supports and rim,
measured pcurve correspondence and a bounded import-only edge tolerance are
required. Original source bytes and the library output are never repaired. Both
original/corrected Boolean comparisons and all before/after import observations
are recorded. See the [capture](sphere_cap_capture.md) for exact limits.

## Expected boundary-free torus rejection

`part-torus-001` passes the five reader stages and records STEP as unsupported.
The exact frozen API rejection is `unsupported_format` at partition byte 2078,
node 39: the complete toroidal face has no boundary loops. The runner checks
the typed error and absence of output before validating the native torus oracle.
That oracle must preserve both full periodic directions, two exact circular
seams and their common vertex, with no degenerate pole edges. An expected
rejection is never counted as a successful library STEP export.

## Expected meridional torus rejection

`part-torus-cut-001` passes the five reader stages and records a STEP export
limitation. Its actual API error is `invalid_record` at partition byte 2398,
node 41: valid meridional circles are currently rejected as tilted. The frozen
rejection is checked exactly, separately from native-oracle validation. The
corpus outcome `unsupported` does not rewrite the actual API error code.

The native oracle requires two independent meridional disks, proper material
normals and the correct clipped quadrant. Its parallel seam must have an exact
constant-V torus pcurve. Positive-weight rational Beziers additionally require a
homogeneous Bernstein whole-curve radius bound within fixed tolerances.
Periodic UV probes are lifted into the actual unwrapped trimmed chart.

## Native circular-rim fillet

`part-fillet-001` applies a native R2 mm fillet to an R10/H20 mm cylinder's top
edge, selected by observed native geometry and its returned EDGE reference.
The resulting two planes, cylinder and torus pass all six stages. Independent
OCCT construction, analytic measures/centroid, material normals and tangent
joins verify the feature result. The imported rational torus meridian requires
an exact constant-U pcurve and a whole-curve bound about its offset circle
center. This passing toroidal band does not cover the unsupported meridional
torus-cut boundary family. See the [capture](fillet_capture.md).

## Exact circular-rim chamfer

`part-chamfer-001` constructs C2 x 45-degree geometry on an R10/H20 mm cylinder
by full polygon revolution. The MCP has no native Chamfer feature; this covers
geometry rather than feature semantics. Its cone band and sharp normal changes
must distinguish it from the fillet with identical ring locations and topology.
Native, exported and independently kernel-chamfered B-reps must agree in
placement, supports, ring associations, straight seams, material normals,
measures and bidirectional solid differences. See the [capture](chamfer_capture.md).

## Elliptic swept mantle and mass precision

`part-elliptic-profile-001` adds a native ellipse extrusion with a typed swept
surface. All five reader stages pass. The STEP exporter rejects the mantle;
the exact `unsupported_format` diagnostic, offset and absence of output are
required. The independent native STEP oracle certifies rational ellipse spans
and a straight extrusion, uses span-aware Gauss-Kronrod volume integration and
boundary-derived area, and compares against an analytic kernel extrusion.
The native API's default mass accuracy is recorded as a separate limitation:
`1e-3` relative scalar admission allowance, fixed `1e-8` m geometry tolerance,
and strict `1e-9` relative agreement between saved fields and frozen native
observations. No geometry check inherits the scalar allowance. See the
[capture](elliptic_profile_capture.md).
