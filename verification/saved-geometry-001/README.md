# Native saved-geometry identity verification

These four original synthetic SolidWorks 2025 SP5 snapshots verify the
configuration/partition resolver, separately from the corpus's six-stage
geometry/export cases. Code, evidence and native files use the repository's
MIT license. No company geometry or imported CAD was used.

The current MCP was inspected live: 53 tools, command schema 1.12. Authentication
used a Bearer key supplied at runtime; authorization headers and the key are not
stored in this dataset. `capture.json` records request bodies and native
responses; `tools.json` records the inspected tool schemas. Failed read or
argument-validation requests remain visible in the journal.

- `baseline.sldprt`: Default, one R10/H20 mm cylinder at the origin.
- `default-active.sldprt`: Default has that one cylinder. TwoBodies additionally
  has an independent R5/H10 mm cylinder at X=40 mm. Configuration-local
  suppression excludes the second feature only from Default. Default is active.
- `two-active.sldprt`: the same configuration geometry with TwoBodies active.
- `sheet.sldprt`: Default has one 20 x 30 mm planar sheet at Z=0.

Each snapshot was saved individually with an immutable, hashed artifact receipt,
then reopened. The reopened active configuration and native topology were
checked, and only the created documents were closed. Sheet mass/body measurement
is unsupported by the current native query; its sheet type is verified through
native B-rep descriptions and topology before save and after reopen.

The selected sheet baseline is an important negative case: it contains one
WORLD node and no BODY, although SolidWorks reports one sheet. A readable sheet
BODY also exists in internal feature geometry. Independent schema inspection in
`sheet-base-inspection.json` records the empty baseline. No fallback promotes
that internal BODY to a final-state result. No delta is applied by the resolver.

`expected.json` keeps native model observations separate from the reviewed
per-payload baseline inventory. Matching body counts in the cylinder snapshots
are fixture observations, not a generic proof of final membership. The manifest
hashes original bytes and evidence. The dataset README itself is explanatory
and is outside that artifact list.

Run offline after building OpenSWX:

```sh
python3 tools/verify_saved_geometry.py \
  --swx-dump ../openswx/build/asmbox/swx_dump
```

Matching environment defaults are `OPENSWX_CORPUS_SWX_DUMP` and
`OPENSWX_CORPUS_SAVED_GEOMETRY_DATASET`. Six configuration queries must retain
resolved identities, unsupported saved-state reconstruction and unresolved
final-body membership. The verifier checks all artifact hashes before execution.
To regenerate live, use fresh document handles, operation IDs and native save
paths; the captured mutation IDs must not be replayed against existing documents.
