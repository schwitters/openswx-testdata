# Library regression contract

The repository includes an offline integrity/admission validator and a working
six-stage runner for the captured cylinder. See [the capture](cylinder_capture.md)
for its native evidence, commands and exact checkpoint scope. Other cases remain
planned. No library result is inferred from a manifest.

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
