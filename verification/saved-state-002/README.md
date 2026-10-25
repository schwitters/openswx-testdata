# Saved baseline and historical delta regression

These six original synthetic SolidWorks 2025 SP5 snapshots and their evidence
use the repository's MIT license. They were constructed from the coordinates
below, without opening or importing private/company CAD. This is a verification
dataset, separate from the corpus's six-stage STEP export cases.

The profile in an explicitly created XY plane has points in metres:
`(0,0), (.01,0), (.01,.018), (.008,.02), (0,.02)`.
A full revolution about its construction line at X=0 produces a simple solid
with a bevel. The MCP has a native revolve and fillet constructor; no chamfer
feature constructor was needed or assumed. A 1 mm fillet rounds the circular
edge at Y=0. Two separate helper sketches contain one line each, from X=.03 to
X=.04 at Y=0 and .005. They do not add final solid/sheet bodies.

| Snapshot | Native final body kinds | Native faces | Baseline/current mark identifier |
| --- | --- | --- | --- |
| turned | solid | 4 | 5 |
| rounded | solid | 5 | 9 |
| suppressed | solid | 4 | 5 |
| restored | solid | 5 | 13 |
| auxiliary-active | solid, sheet | 6 | 13 |
| auxiliary-suppressed | solid | 5 | 13 |

The rounded feature is explicitly suppressed and restored between snapshots.
Each snapshot is individually saved with an immutable artifact receipt, read
back with SHA-256 verification, closed and reopened for native configuration,
body/topology, B-rep and feature inventory checks. Only created documents are
closed. The original construction and native evidence are in `capture.json`;
request bodies are retained, without authorization headers or credentials.
One read-only request returned busy with `outcome_unknown: false`; its successful
retry is recorded separately. A capability query rejected for missing `params`
is also retained alongside the corrected query. All created/reopened documents
were closed.
`tools.json` records the 53 inspected MCP tool schemas (command schema 1.12).

After reopening `restored`, a 10 x 15 mm planar sheet is created at X=.04,
normal +Z, with UV bounds `[0,.01,0,.015]`. It is saved active and then explicitly
suppressed and saved again. Native B-rep queries include solid and sheet bodies,
including hidden bodies, and finish without pagination. The two snapshots have
**the same kernel state identifiers and candidate body kinds, but different
native final body sets**. Both store a sheet in FeatureBodies/LocalBodies and
one solid in the configuration partition. This guards against both blindly
adding internal candidates and treating identifier equality as completeness.

`byte-inspection.json` is a separate audit from `parasolid_inspect --nodes`,
recording extracted payload provenance, BODY types and administrative fields.
`expected.json` separates these reviewed byte expectations from native oracle
results. Native body inventories are compact projections of the full B-rep
responses retained in the capture journal. The manifest hashes every admitted
artifact; this explanatory README is outside that artifact list.

After building OpenSWX, run from this corpus repository:

```sh
python3 tools/verify_saved_geometry.py \
  --swx-dump ../openswx/build/asmbox/swx_dump \
  --dataset verification/saved-state-002
python3 -m unittest discover -s tests -p 'test_saved_state_evidence.py'
```

The CLI verifies matching identifier evidence and a one-mark structural path.
It must still report `state_status: unsupported` and
`body_membership_status: unresolved`, and never treat delta node images as a
standalone body inventory. Synthetic C++ fixtures additionally check a different
baseline, another history branch, conflicts, cycles, missing links, reordered
marks, full-width words and unset metadata. No native transition-required
capture has yet been established; those C++ cases are parser/graph regressions,
not evidence of automatic real-file replay.
