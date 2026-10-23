# openswx-testdata

An MIT-licensed test corpus repository for `libopenswx`,
`libopenparasolid` and `libopenswstep`. The first producer target is
**SolidWorks 2025**. All future CAD fixtures must be original synthetic models
with recorded authorship and generation provenance.

**Current state: 50 planned cases, nineteen recipes and nineteen captured parts.**
The [cylinder](docs/cylinder_capture.md), [block](docs/block_capture.md),
[tube](docs/tube_capture.md), [blind-hole](docs/blind_hole_capture.md),
[through-hole](docs/through_hole_capture.md),
[stepped-bore](docs/stepped_bore_capture.md), [two-bores](docs/two_holes_capture.md),
[concave L-profile](docs/concave_profile_capture.md),
[multiple solids](docs/multiple_solids_capture.md),
[thin wall](docs/thin_wall_capture.md),
[cone frustum](docs/cone_frustum_capture.md),
[cone sector](docs/cone_sector_capture.md), [sphere](docs/sphere_capture.md),
[sphere cap](docs/sphere_cap_capture.md), [torus](docs/torus_capture.md),
[torus segment](docs/torus_cut_capture.md), [native fillet](docs/fillet_capture.md),
[exact chamfer](docs/chamfer_capture.md) and
[elliptic extrusion](docs/elliptic_profile_capture.md) captures
include native SLDPRT, Parasolid binary/text and STEP AP214 references, full
capture provenance and a shared offline check of
all three libraries. Fifteen cases pass all six stages. The full sphere and
torus pass the five reader stages; their boundary-free faces produce verified
`unsupported_format` STEP export results. The meridionally trimmed torus is a
third export limitation, currently rejected as `invalid_record` despite valid
native geometry. The elliptic extrusion adds a fourth limitation: its swept
mantle is currently rejected as `unsupported_format`. Its default native mass
precision and independent geometric checks are documented separately.
The general MCP generation adapter is still pending.
The local audit checks contracts and artifact integrity; library/OCCT
verification is a separate runner.

## Start locally

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python tools/corpus.py
.venv/bin/python -m unittest discover -s tests -v
```

The audit exits with code 2 on invalid contracts, missing artifacts, changed
bytes, inconsistent export receipts or failed analytic checks. Add
`--require-ready` to reject an empty corpus. `--root` selects another checkout;
the matching environment variables are `OPENSWX_CORPUS_ROOT` and
`OPENSWX_CORPUS_REQUIRE_READY=1`.

## Layout

- `plan.json`: 50 individually named cases, P0/P1/P2 priorities, coverage targets
  and semantic capabilities. Entries are plans, not coverage claims.
- `recipes/`: declarative, metre/radian construction instructions for a block,
  cylinder, tube, blind hole, through hole, stepped bore, two bores, a concave
  L-profile, two separate solid bodies, a plate with 10 micrometre thickness,
  a revolved cone frustum, a 90-degree cone sector, a complete sphere, a minor spherical cap, a ring torus, a quarter-torus segment, a native cylinder rim fillet, a revolved exact chamfer and a native ellipse extrusion.
  Step names are not promises about deployed MCP tool names.
- `schemas/`: JSON Schema 2020-12 contracts for the plan, starter recipes,
  captured cases, native observations and export receipts. STEP protocol, file
  version and source-to-metre scale are recorded separately.
- `cases/<id>/`: admitted immutable fixtures and `case.json`; currently `part-cylinder-001`,
  `part-block-001`, `part-tube-001`, `part-blind-hole-001`, `part-through-hole-001`, `part-stepped-bore-001`, `part-two-holes-001`, `part-concave-profile-001`,
  `part-multiple-solids-001`, `part-thin-wall-001`, `part-cone-frustum-001`, `part-cone-sector-001`, `part-sphere-001`, `part-sphere-cap-001`, `part-torus-001`, `part-torus-cut-001`, `part-fillet-001`, `part-chamfer-001` and `part-elliptic-profile-001`.
- `tools/corpus.py`: offline contract, provenance-association and SHA-256 audit.
- `tools/run_case.py`: shared six-stage offline regression runner, using explicit
  manifest selection and fixture-specific OCCT geometry checks.
- `tests/`: temporary admission/error contracts plus captured artifact integrity
  and native geometry-sample checks. Optional OCCT tests also reject equally
  sized but misplaced/differently proportioned blocks, eccentric bores and reversed
  blind-hole entry.
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
one-body block/cylinder/tube parts, the top-entry cylindrical blind hole and
the block with one or two through bores, the coaxial stepped bore and the
extruded L-profile with concave caps. The multiple-solids recipe adds two
separated blocks, individual body measures and explicit selection of both bodies.
The thin-wall case reuses the block recipe with 10 micrometre extrusion depth.
All ten planned P0 cases and the first two P1 cases (cone frustum and cone
sector) now have captured fixtures and offline library checks. The sphere adds
a third P1 fixture with a known unsupported STEP export. The minor sphere cap
adds a passing fourth P1 fixture, with an explicit native OCCT projection
workaround documented in its capture report. The fifth P1 fixture, a full
ring torus, adds a second expected unsupported STEP export. The sixth P1 case,
a quarter torus with meridional end disks, exposes a third export limitation.
The seventh P1 case, a native R2 mm cylinder rim fillet, passes STEP export
with a toroidal blend band. The eighth P1 case, a C2 x 45-degree circular-rim
chamfer, also passes. It uses an exact revolved polygon because the MCP lacks a
native Chamfer feature. The ninth P1 fixture, an elliptic extrusion, passes all
five reader stages and records an unsupported swept-surface STEP export.
The revolution contract permits full or partial turns of an XZ polygon, or a
full turn of a right semicircle, minor spherical-cap profile or offset circle, about document +Z through the origin;
construction and analytic angles must agree.
Extend and test those contracts before capturing the other planned cases. Configuration, history, assembly and drawing
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
The corpus includes selected extracted payloads as explicitly marked derived
artifacts, plus capture evidence and validation reports. Native reference files
remain unchanged. See [known limits](docs/known_limits.md) for the standalone
Parasolid envelope and explicit checkpoint-selection scope.

Generated trial files belong in ignored `staging/`; transient reports and
exporter outputs belong in ignored `results/`.

The repository has no remote publication configured. Git LFS is not required
for this small initial corpus; decide from actual fixture sizes before a
large data batch.
