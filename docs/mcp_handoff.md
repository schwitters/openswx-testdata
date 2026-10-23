# MCP integration handoff

This repository prepares the consumer side of the requested SolidWorks tools.
It does not implement or modify the server. The companion requirements are
`sw-agent/docs/openswx_test_data_tools_requirements.md` in the sw-agent project.

## Capability mapping to establish after deployment

`plan.json` uses semantic names. The future adapter must map each name to an
actual discovered tool, input schema, output schema and effective runtime
support. The names below reflect the original requirements. Admitted captures now
include the actual deployed tool catalog and effective capabilities; use those
frozen snapshots as the authority for reproducing their requests.

| Semantic capability | Required behavior | Proposed/existing interface |
| --- | --- | --- |
| Discovery | Actual schemas, limits, native build and worker version | MCP `tools/list`; proposed `sw.capabilities.get` |
| `construction.extrude` | Fresh part, XY sketch profiles, exact new/join/cut extrusion | Existing sketch/feature creation tools |
| `export.native` | Save, close/reopen and identify the persisted configuration | Existing document commands |
| `export.parasolid_binary` | Whole-document `.x_b`, explicit effective units/version | Extended save or proposed document export |
| `export.parasolid_text` | Whole-document `.x_t`, explicit effective units/version | Same export contract |
| `export.step_ap214` | Whole-document STEP, verified AP214 | Same export contract |
| `native.measure` | Body count, native area/volume and known SI conversion | Extended native measurement |
| `native.brep` | Revision-scoped body/face/loop/edge/vertex graph, geometry/tolerances | Proposed `sw.model.brep.describe` |
| `native.evaluate` | Native curve/surface domains and point/derivative evaluation | Proposed `sw.geometry.evaluate` |
| Artifact transport | Immutable size/hash and complete bytes | Shared directory or proposed artifact describe/read |

Advanced construction, transforms, configurations, assemblies and drawing
capabilities are deferred according to the plan. Do not mark a capability
available because a tool name exists: require supported options and a successful
small readback/capture probe.

## Adapter boundary

The generation adapter should consume a recipe and produce a staged case. It
owns command envelopes, operation IDs, document handles, revision guards,
retries and artifact transport. Store recipe step IDs in the recipe; resolve
returned native IDs only within the run. Sketch operations with the same
`sketch_id` add contours to one sketch; the tube recipe therefore creates two
concentric loops in one profile, not two independent solid extrusions. Do not embed Windows session handles
in recipes or treat ordinal body IDs as persistent cross-file identities.

Record the discovery response, native readbacks, receipts and effective settings.
Do not store credentials or authorization headers. Preserve native warnings;
a warning is not automatically a failure, but an unverified export option is
not an acceptable verified receipt.

The adapter must not invoke the libraries under test to create native expected
geometry. Expectations come from analytic construction and native readback.
Extraction output can become a byte-level extraction regression fixture only
after the captured bytes have been independently reviewed/verified.

## Acceptance sequence when tools arrive

1. Read-only discovery and capability/schema mapping.
2. One cylinder probe in a fresh document, including save/reopen, measurement,
   all three reference formats and local artifact verification.
3. Confirm exports did not change geometry, revision or effective configuration.
4. Admit the cylinder and implement the Linux per-stage runner against this
   concrete format of producer readbacks.
5. Capture the block and tube, then repeat the cylinder independently to check
   semantic reproducibility.
6. Expand tools/adapter/contracts only where the next named case requires it.

Do not use a mock discovery response as evidence that these acceptance steps
have passed. Contract tests deliberately use temporary dummy bytes and are not
native format verification.
