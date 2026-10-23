# Captured thin wall: part-thin-wall-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, is a rectangular
plate at the origin, 20 x 30 mm in XY and **0.01 mm (10 micrometres) thick** along
+Z. Configuration is `Default`. One rectangular sketch on an explicit XY plane
is extruded into a new body. The recipe uses the existing analytic block
contract, with a small height; no new native construction tool is required.

The configured-default part was empty and had no custom properties. Template
file identity remains unavailable. The part was saved, closed, reopened and saved
with immutable artifact capture. Actual document handles are retained from
producer responses. Reference exports preserved geometry, configuration,
semantic revision and native update stamp. Only this run's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 40,597 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 6,673 | metre; 36.01.228 |
| Parasolid text | 7,175 | metre; 36.01.228 |
| STEP | 13,567 | millimetre; ISO-10303-21, AP214 |

Downloaded hashes and sizes match producer receipts. Source topology is one
solid, six planar faces, twelve straight edges, eight vertices and one connected
shell. All six face loops remain present.

## Independent expectations

- Volume: `20*30*0.01 = 6` mm^3.
- Boundary area: `2*(20*30+20*0.01+30*0.01) = 1201` mm^2.
- Centroid: (10,15,0.005) mm.
- Minimum feature size: `1e-5` m, the declared and independently checked thickness.
- Binding tolerance: `1e-8` m, unchanged from the other captures.
- Feature-to-binding-tolerance ratio: 1,000.

The smallest dimension is recorded in `validation/observations.json`, together
with the binding tolerance and their ratio. This is one resolved thickness test,
not a certified minimum wall thickness for SolidWorks or the libraries. Native
geometry APIs do not expose certified error bounds. The independent checker uses
absolute positional checks of `1e-8` mm on expected corners and planes; it does
not increase matching tolerances to the feature size.

Ninety native curve/surface samples cover all twelve lines and six planes. The
four short vertical edges must still span the full 10 micrometres. Four corners
remain on each of the two distinct Z planes. Both cap normals are checked for
opposite outward directions. Side samples retain their native trim membership
and material normals.

## Reader and STEP evidence

The 6,738-byte embedded partition decodes 180 nodes, including twelve line, six
plane and eight point geometries. It has no model/reference/geometry issues.
The 1,124-byte delta has two ordinary schema nodes, two delta nodes and two
packets. Both streams decode completely with no uninterpreted bytes. Explicit
partition 0, BODY 2 passes topology and geometry binding without interval
overrides.

The exporter preserves six faces, twelve edges and eight vertices without
synthetic seams. OCCT imports native and library STEP as valid single-solid
B-reps with those counts. Both exact positioned corner sets, all straight edge
connections, all six supporting planes and outward material normals are checked.
The helper is shared with the multiple-solids checker. Both volume and surface
area agree with the independent formula, and bidirectional solid-difference
volumes are zero.

Negative kernel tests reject thicknesses of 9 and 11 micrometres, a 1-micrometre
translation, swapped XY extents, a different thin axis, a plate collapsed into a
single face and inverted material orientation. Translation and swapped extents
preserve volume and surface area, so measures alone cannot certify placement or
axis orientation.

The [existing limits](known_limits.md) remain: explicit checkpoint matching is
not automatic history reconstruction. Native standalone `.x_b` ASCII headers
and `.x_t` text grammar are not supported by the binary reader.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case), with a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-thin-wall-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/thin-wall-run-001
```

This capture completes the ten planned P0 cases. P1 analytic/freeform geometry
and P2 configurations, history, assemblies and drawings remain planned; P0
coverage is not a claim of complete format support.
