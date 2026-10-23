# openswx-testdata

An MIT-licensed corpus preparation repository for `libopenswx`,
`libopenparasolid` and `libopenswstep`. The first producer target is
**SolidWorks 2025**. All future CAD fixtures must be original synthetic models
with recorded authorship and generation provenance.

**Current state: 50 planned cases, three starter recipes, zero captured cases.**
No SolidWorks/MCP generation adapter or library regression runner is implemented
here yet. The local audit checks contracts and artifact integrity; it does not
claim a CAD file is valid or a library supports it.

## Start locally

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/corpus.py
.venv/bin/python -m unittest discover -s tests -v
```

The audit exits with code 2 on invalid contracts, missing artifacts, changed
bytes, inconsistent export receipts or failed analytic checks. Add
`--require-ready` to reject an empty corpus. This deliberately fails until at
least one captured case is admitted. `--root` selects another checkout; the
matching environment variables are `OPENSWX_CORPUS_ROOT` and
`OPENSWX_CORPUS_REQUIRE_READY=1`.

## Layout

- `plan.json`: 50 individually named cases, P0/P1/P2 priorities, coverage targets
  and semantic capabilities. Entries are plans, not coverage claims.
- `recipes/`: declarative, metre/radian construction instructions for a block,
  cylinder and tube. Step names are not promises about deployed MCP tool names.
- `schemas/`: JSON Schema 2020-12 contracts for the plan, starter recipes,
  captured cases, native observations and export receipts.
- `cases/<id>/`: admitted immutable fixtures and `case.json`; currently empty.
- `tools/corpus.py`: offline contract, provenance-association and SHA-256 audit.
- `tests/`: contract tests using temporary dummy bytes, not CAD fixtures.
- `docs/`: the capture procedure, tool handoff and staged testing contract.

See [the first capture procedure](docs/first_capture.md),
[the MCP handoff](docs/mcp_handoff.md), and
[the regression contract](docs/regression_contract.md).

## Fixture admission

Every admitted case must carry explicit per-stage expectations, producer build,
worker version, timestamp, configuration, document revision, tolerances,
authorship and hashes of all artifacts. The first part captures require:

```text
cases/part-cylinder-001/
  case.json
  source/model.sldprt
  reference/native.json
  reference/model.x_b
  reference/model.x_t
  reference/model.step
  provenance/capabilities.json
  provenance/exports.json
```

Paths under the case directory are declared in `case.json`. Export receipts
must reference those same bytes, revision and configuration. Unknown native
fields are omitted and named in `unavailable_fields`; they are never filled
with guessed zeros. Source and export body IDs are not assumed to coincide.

The validator's native observations are normalized capture data. Preserve
original MCP readbacks in the native `observations` object or as additional
explicitly declared provenance in a future contract extension. Effective
options and version verification must come from the producer's response, not
from file extensions or requested settings.

The starter recipe language and analytic admission checks currently cover only
one-body block/cylinder/tube parts. Extend and test those contracts before
capturing the other planned cases. Configuration, history, assembly and drawing
cases are intentionally queued for later batches.

## Versioning and licensing

Code, recipes, documentation and original fixture data in this repository use
[MIT](LICENSE). Fixture provenance must explicitly identify the author and
license. Do not copy private industrial models, templates, title blocks or
reference exports into this corpus. Use corpus-owned templates and dependencies.
Record any future contribution's provenance before admission.

Never silently overwrite an admitted fixture. Regeneration is a reviewed change
with new hashes, producer receipts and a semantic comparison. Binary identity
between independent SolidWorks saves is not required. Linux library CI will
consume a pinned corpus Git commit, without contacting SolidWorks or the MCP.
Generated trial files belong in ignored `staging/`; transient reports and
exporter outputs belong in ignored `results/`.

The repository has no remote publication configured. Git LFS is not required
for the empty initial corpus; decide from actual fixture sizes before the first
large data batch.
