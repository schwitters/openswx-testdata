# Native isolated-cone-apex regression

Two original synthetic SolidWorks 2025 SP5 parts reproduce the failure
`Ruled patches require one non-isolated loop`. All fixtures, recipes and
provenance use the repository's MIT license. No private part, private STEP,
imported geometry or measurements from a private model were used to construct
these primitives. This verification dataset is separate from the nineteen
six-stage cases in `cases/` and does not change the 50-case plan.

The declarative [recipe](recipe.json) records coordinates in metres and angles
in radians. The complete MCP request/response journal is in `capture.json`,
without authorization headers or credentials. Tools and capabilities were
inspected live (command schema 1.12). Every native source was saved to an immutable
artifact, downloaded with SHA-256 verification, closed and reopened. Native
measurements and B-rep observations were then captured, and SolidWorks produced
an AP214 reference. Export left the measured geometry unchanged. Only generated
documents were opened/closed; document and configuration custom properties were
also checked. All generated documents are closed.

| Fixture | Construction | Native source topology | Isolated apex |
| --- | --- | --- | --- |
| cone | Full revolution of `(0,0), (6,0), (0,10)` mm in XZ about +Z | 1 solid, 2 faces, 1 edge, 1 vertex | Z=10 mm |
| blind-drill | R15/H30 mm cylindrical blank; full revolved cut with R4 mm bore from Z=30 to Z=20 and conical tip at Z=17.5 | 1 solid, 5 faces, 4 edges, 1 vertex | Z=17.5 mm |

Both source conical faces have exactly two loops: a one-edge full circular loop
and an isolated vertex loop. The drill case additionally exercises an inward
material normal, as occurs at a conical blind-hole bottom. The native AP214
references use one circular `FACE_OUTER_BOUND` on each `CONICAL_SURFACE`, with
the apex implicit in the surface singularity. OCCT reconstructs the apex,
periodic seam and degenerate pole edge when importing that representation.

`source-inspection.json` records independent Parasolid geometry/topology reports.
`expected.json` keeps reviewed byte identities separate from native measurements
and specifies the explicit selected partition/BODY. The selection is a verified
checkpoint, not a generic reconstruction of the SolidWorks saved state.
`receipts.json` and `manifest.json` verify artifact identity. The explanatory
README itself is outside the manifest's artifact list.

## Regression and independent oracle

`regression-control.json` records the observed before/after result. The old
`body_writer.cc` from OpenSWX `b419a94` was compiled against otherwise unchanged
library code: both inputs return `unsupported_format` with the intended message
and leave no output file. OpenSWX fix `2b4e029` exports every regular source edge
and every face, without increasing the tolerance or dropping a face.

`tools/verify_cone_apex.py` repeats six stages for each native source:

1. Saved metadata against the native measurements.
2. Extraction with frozen inventory and exact payload hashes.
3. Complete decoding of every embedded payload.
4. Source body topology and the explicit isolated-apex/circular-loop pattern.
5. Complete body geometry binding at the unchanged 1e-8 m tolerance.
6. Full STEP export, the native one-bound cone representation and independent
   OCCT comparison with the SolidWorks STEP.

The geometric checker verifies analytic support families, apex placement, the
whole cone's radius law at multiple interior parameters, material normals,
circular rim coverage, cap trimming, complete topology, area and volume.
Bidirectional solid differences must be below 1e-6 mm³. The cone has volume
`120*pi` mm³ and area `pi*(36+6*sqrt(136))` mm². The drill has volume
`pi*(6750-160-40/3)` mm³ and area
`pi*(900+225+209+80+4*sqrt(22.25))` mm².

Tests also construct independent OCCT solids. Wrong taper with equal scalar
measures, translated geometry, inverted material orientation and a flat-bottom
substitute must fail. This prevents a count-only or volume-only success.

## Run offline

Use an OpenSWX checkout containing fix `2b4e029`. Build its normal `swx_dump` and
`parasolid_inspect` targets, then build the existing generic export driver:

```sh
cmake -S tools -B /tmp/openswx-apex-export \
  -DOPENSWX_SOURCE_DIR=/absolute/path/to/openswx
cmake --build /tmp/openswx-apex-export --target case_export
python3 tools/verify_cone_apex.py \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-apex-export/case_export \
  --occt-python /absolute/path/to/ocp-venv/bin/python \
  --output /tmp/openswx-apex-verification
```

Install the existing `requirements-occt.txt` into the optional OCCT interpreter.
The output directory must be new; omitting `--output` uses a temporary directory
and prints the JSON report. An optional `--baseline-exporter` repeats the
pre-fix failure/no-partial-file check with a separately built old driver.
Every option has an environment equivalent: `OPENSWX_CORPUS_BUILD`,
`OPENSWX_CORPUS_EXPORTER`, `OPENSWX_CORPUS_OCCT_PYTHON`,
`OPENSWX_CORPUS_BASELINE_EXPORTER`, `OPENSWX_CORPUS_OUTPUT` and
`OPENSWX_CORPUS_CONE_APEX_DATASET`.

```sh
python3 -m unittest discover -s tests -p 'test_native_cone_apex.py' -v
```

Frozen evidence tests always run. Geometric negative tests run when OCP is
installed in that Python interpreter. The native library integration test runs
when `OPENSWX_CORPUS_BUILD`, `OPENSWX_CORPUS_EXPORTER` and
`OPENSWX_CORPUS_OCCT_PYTHON` are set; adding the baseline variable enables the old
failure control. These fixtures and checks do not certify other apex trim types,
additional boundaries or automatic saved-state/final-body reconstruction.
