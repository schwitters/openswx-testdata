# Captured cylinder: part-cylinder-001

The first admitted case was generated with SolidWorks 2025 SP5, revision
33.5.0, through the deployed MCP tools. It has radius 0.01 m, height 0.02 m,
axis +Z, lower cap at Z=0 and configuration `Default`.

The run created an empty part, an explicit XY support plane, a circular sketch
and a blind new-body extrusion. It saved, closed and reopened the native part,
then saved/captured the reopened state. Geometry and the native update stamp
were unchanged by reference export. Only documents created by this run were
closed. No pre-existing SolidWorks document was modified.

The four downloaded artifacts are:

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 85,017 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 3,852 | metre; 36.01.228 |
| Parasolid text | 4,182 | metre; 36.01.228 |
| STEP | 6,634 | millimetre; ISO-10303-21, AP214 |

All hashes match the native export receipts. Raw MCP discovery, construction,
save/reopen, B-rep, native evaluations and export receipts are retained.
Twenty-six native curve/surface samples independently satisfy the cylinder/cap
geometry; numerical tolerances are recorded in `case.json`.

Native reference values are approximately 6,283.185307179587 mm^3 volume and
1,884.955592153876 mm^2 total boundary area. The embedded partition has two
circle curves, two planes and one cylinder support, with no geometry/model
issues. Recorded incidence and complete body binding succeed without explicit
interval overrides.

The selected checkpoint exports to STEP. OCCT 7.9 independently imports both
that output and SolidWorks' STEP, validates both B-reps, checks analytic radius,
cap positions, volume and area, and finds zero residual volume for both boolean
subtractions. The [known limits](known_limits.md) distinguish this successful
checkpoint export from automatic history resolution and standalone native
Parasolid-file parsing.

## Repeat the Linux checks

Use a clean openswx checkout and its normal build containing `swx_dump` and
`parasolid_inspect`. The small export driver builds against the selected source
checkout; its payload/body constants belong only to this frozen cylinder.

```sh
cmake -S tools -B /tmp/openswx-cylinder-build \
  -DOPENSWX_SOURCE_DIR=/absolute/path/to/openswx
cmake --build /tmp/openswx-cylinder-build --target cylinder_export --parallel 4
python3 -m venv /tmp/openswx-corpus-occt
/tmp/openswx-corpus-occt/bin/python -m pip install -r requirements-occt.txt
.venv/bin/python tools/run_cylinder.py \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-cylinder-build/cylinder_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/cylinder-run-001
```

The report directory must be new. It receives per-operation stdout/stderr,
extracted payloads, generated STEP and `report.json`. Those are run outputs,
not replacements for frozen native reference data. The six stages must all
pass; the original native binary reference must still produce the separately
recorded expected unsupported-envelope diagnostic until that issue is reviewed.

Runner options also accept `OPENSWX_CORPUS_ROOT`, `OPENSWX_CORPUS_BUILD`,
`OPENSWX_CORPUS_EXPORTER`, `OPENSWX_CORPUS_OCCT_PYTHON` and
`OPENSWX_CORPUS_OUTPUT`. Preserve a venv's interpreter path rather than resolving
its symlink to the system interpreter.
