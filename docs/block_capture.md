# Captured block: part-block-001

This original synthetic part was generated in a fresh empty SolidWorks 2025 SP5
part, revision 33.5.0. Its dimensions are 20 x 30 x 40 mm along X, Y and Z,
with opposite corners at (0,0,0) and (20,30,40) mm and configuration `Default`.

Construction used an explicit XY support plane, four rectangle lines and a
40 mm blind new-body extrusion. The run saved, closed and reopened the document,
then saved/captured the reopened state. Native geometry, configuration, semantic
revision and update stamp were unchanged by reference export. The run closed
only its own documents. Document/configuration custom properties were empty.
The configured default template's file identity remains unavailable, as in the
[first capture](known_limits.md#template-provenance).

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 58,517 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 6,665 | metre; 36.01.228 |
| Parasolid text | 7,124 | metre; 36.01.228 |
| STEP | 13,533 | millimetre; ISO-10303-21, AP214 |

All downloaded hashes match the producer receipts. Native measurements confirm
one solid, six faces, twelve edges, eight vertices, one connected shell,
24,000 mm^3 volume, 5,200 mm^2 area and centroid (10,15,20) mm. Ninety native
samples cover all twelve line curves and six plane surfaces, including trim
membership for the surface samples.

The saved part contains one embedded partition and one delta stream. Both decode
completely without uninterpreted bytes. The partition has 180 nodes, including
twelve lines, six planes and eight point geometries, with no model/geometry
issues. Its explicit BODY 2 passes recorded topology and body binding without
interval overrides. XT includes both material-side and void-side shell uses;
those are not two separate physical solids.

The selected checkpoint exports as one solid with six faces, twelve edges and
eight vertices. OCCT imports the native and library STEP, validates both B-reps,
checks the analytic measures and all eight corner positions, and verifies every
edge is straight and every face planar. The bidirectional solid-difference
volume is zero. Unlike the cylinder case, no synthetic ring vertices or periodic
seam edges are needed.

The same limitations remain explicit: this is independently verified checkpoint
selection, not automatic delta/current-state reconstruction, and the standalone
native `.x_b` still has an unsupported ASCII envelope before its binary PS
prologue. See [known limits](known_limits.md).

<a id="repeat-either-admitted-case"></a>

## Repeat an admitted starter case

The generic export driver accepts the manifest's explicit payload and body IDs.
It uses metre coordinates and a 1e-8 m binding tolerance for these starter cases;
it does not infer history state or units for arbitrary inputs.

```sh
cmake -S tools -B /tmp/openswx-corpus-build \
  -DOPENSWX_SOURCE_DIR=/absolute/path/to/openswx
cmake --build /tmp/openswx-corpus-build --target case_export --parallel 4
.venv/bin/python tools/run_case.py \
  --case part-block-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/block-run-001
```

Install `requirements.txt` in the runner environment and `requirements-occt.txt`
in the OCCT environment. The openswx build must provide `swx_dump` and
`parasolid_inspect`. Use a new report directory for every run. Change `--case` to
`part-cylinder-001`, `part-tube-001`, `part-blind-hole-001` or
`part-through-hole-001`, `part-stepped-bore-001`, `part-two-holes-001` or
`part-concave-profile-001` or `part-multiple-solids-001` or
`part-thin-wall-001` or `part-cone-frustum-001` or `part-cone-sector-001` or `part-sphere-001` or `part-sphere-cap-001` or `part-torus-001` to run the other admitted starters through
the same driver. The older
`run_cylinder.py`/`cylinder_export` entry points remain supported.

`--case` also accepts `OPENSWX_CORPUS_CASE`; the remaining options retain the
[documented runner environment variables](cylinder_capture.md#repeat-the-linux-checks).

The optional OCCT tests exercise incorrect placement and swapped X/Y dimensions;
both have the same volume and area as the reference and must still fail:

```sh
/tmp/openswx-corpus-occt/bin/python -m unittest discover \
  -s tests -p test_step_checks.py -v
```
