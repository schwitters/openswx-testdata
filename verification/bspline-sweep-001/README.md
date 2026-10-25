# Native cubic B-spline sweep fixtures

Two original synthetic SolidWorks 2025 SP5 parts preserve the original
`Swept inversion requires a typed analytic section` failure. Both models and
all associated evidence are MIT licensed. No private geometry or imported CAD
was used. They are verification fixtures, additional to the nineteen six-stage
cases in `cases/`; the 50-case plan is unchanged.

## Construction

The [recipe](recipe.json) gives all poles, expanded knots, reference frames and
depths in metres/radians. Sketch X maps to document +Y and sketch Y to +Z.
The closed cross-section is the convex region **above** the curved profile,
below its final height and to the right of its left wall. Two straight lines
close the spline; extrusion proceeds along document -X.

Use normalized profile coordinate `u` in `[0,1]`. In local millimetres:

| Fixture | Profile law | Origin (mm) | Depth | Clamped cubic poles/spans |
| --- | --- | --- | --- | --- |
| cubic | `Y=12*u`, `Z=9*u^3` | `(0,0,0)` | 8 mm | 4 poles, 1 span |
| multispan | `Y=12*u`, `Z=9*u^3+3*max(u-.3,0)^3-2*max(u-.75,0)^3` | `(20,-10,5)` | 6 mm | 6 poles, 3 spans |

The first curve uses its direct Bernstein controls. The second curve's poles
were derived by exact Fraction collocation at Greville sites, independently of
OpenSWX, with knots `.3` and `.75`. It is a genuine piecewise cubic, not merely
a redundant subdivision of the first polynomial. Both profiles have nonzero
tangents, are monotone in Y and have nonnegative curvature. Their convex planar
end caps avoid introducing a separate nonconvex-profile exporter limitation.

Each model was created in a fresh configured-default part, saved with an
immutable artifact receipt, downloaded with SHA-256 verification, closed and
reopened. Native B-rep queries completed without pagination. Document and
configuration custom properties are empty. Native AP214 references were exported
without changing measured geometry, then only the generated documents were
closed. `capture.json` preserves request bodies and native responses; it contains
no authorization headers or API key. `tools.json`, `capabilities.json` and
`receipts.json` retain the observed producer contract and artifact identity.

## Reproduced boundary

Both sources contain one solid, five faces, nine edges and six vertices. Their
explicit checkpoint is partition payload 0 / BODY 2. Each curved wall has:

- one `SWEPT_SURF` with a fully decoded, nonrational cubic `B_CURVE` section;
- one loop with two B-spline profile edges and two straight generators;
- complete schema decoding, valid references and typed geometry.

The stored sweep points in +X; its generator lies on the opposite end of the
extrusion. This parameterization is distinct from the construction direction.
The native STEP stores the wall as degree `(3,1)`
`B_SPLINE_SURFACE_WITH_KNOTS`, with four planar adjoining faces.

`source-inspection.json` records the exact source pattern. At the recorded
OpenSWX revision, binding fails at face 43 in both fixtures. STEP export returns
`unsupported_format` with the same message and creates **no partial output**;
see `export-errors.json`. These immutable artifacts describe the capture
baseline, rather than the current reader's expected behavior.

The reader now inverts these sections using their strictly monotone transverse
control projection and the source B-spline evaluator. The live runner requires
successful binding of every source face, edge and vertex. STEP export now emits
an exact degree-(3,1) B-spline surface for the swept wall, retaining the source
profile knots, all five faces, nine edges and six vertices. The library STEP
must pass the same independent polynomial, trim and material-normal oracle as
the native reference. Both directional Boolean differences must stay below
`1e-6 mm³`; a partial body is never accepted.
Rational, closed and nontransverse sections remain outside these fixtures.
Neither an explicitly selected checkpoint nor a successful native export
certifies generic saved-state reconstruction.

## Independent native oracle

`tools/check_bspline_sweep_step.py` imports the native STEP through OCCT and
checks complete topology, support degrees, both profile curves, sampled profile
positions and material normals, planar cap placement and trimming, area and
volume. Exact polynomial cross-section integration gives volumes **648 mm³**
and **545.013225 mm³**. Only the independent reference-area oracle uses numerical
arc-length integration; no approximation is substituted into exported geometry.
Negative tests reject a translated equal-volume body and reversed material
orientation. The nonuniform fixture is separately checked for genuine added
piecewise terms.

The native default mass-property cache is approximate: the recorded volume
relative errors against the independent analytic geometry are about `8.38e-7`
and `4.91e-5`. Saved fields are compared with that native observation, while
OCCT geometry is checked separately at `1e-9` relative measure tolerance.
These are distinct checks; the geometric tolerance was not relaxed to match the
native cache. `occt.json` preserves both observations and their discrepancy.

## Repeat offline

Build the usual `swx_dump` and `parasolid_inspect`, and the existing generic
`tools/case_export.cc` driver described in the cone-apex dataset. Then run:

```sh
python3 tools/verify_bspline_sweep.py \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /absolute/path/to/case_export \
  --occt-python /absolute/path/to/ocp-venv/bin/python \
  --output /tmp/bspline-sweep-verification
python3 -m unittest discover -s tests -p 'test_native_bspline_sweep.py' -v
```

The independent geometry oracle also accepts `--reference native.step`, with
environment variable `OPENSWX_CORPUS_BSPLINE_SWEEP_REFERENCE`, to compare an
exported solid in both Boolean directions against its original native reference.
Explicit CLI values take precedence. The runner supplies this option itself.

The output directory must be new; omitting it uses temporary files. Matching
environment variables are `OPENSWX_CORPUS_BUILD`, `OPENSWX_CORPUS_EXPORTER`,
`OPENSWX_CORPUS_OCCT_PYTHON`, `OPENSWX_CORPUS_OUTPUT` and
`OPENSWX_CORPUS_BSPLINE_SWEEP_DATASET`. Native integration tests run when the first
three are set; geometric tests require the existing optional OCP dependency.

The runner expects metadata, extraction, decoding, topology and complete body
binding and STEP export to pass. The resulting solid must retain complete source
topology and pass the native geometric oracle and bidirectional solid differences.
The immutable captured failures remain historical evidence; live verification
must no longer reproduce either the old inversion or surface-writer limit. The manifest hashes all admitted artifacts;
this explanatory README is outside that artifact list.
