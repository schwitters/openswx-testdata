# Captured multiple solids: part-multiple-solids-001

This original synthetic SolidWorks 2025 SP5 part, revision 33.5.0, contains two
disjoint blocks in configuration `Default`:

| Native key | Origin, mm | Dimensions, mm | Embedded BODY |
| --- | --- | --- | ---: |
| `large-block` | (0,0,0) | 20 x 30 x 40 | 6 |
| `small-block` | (50,0,0) | 10 x 15 x 20 | 2 |

Two rectangular sketches on an explicit XY plane are independently extruded
with `new_body`. The X clearance is 30 mm. No imported geometry is involved.
Native body enumeration lists the large block first, whereas the embedded
partition assigns BODY 2 to the small block. Neither enumeration order nor
numeric IDs imply geometric identity. The manifest records both explicit IDs
and their native keys, verified independently against positioned geometry.

The fresh part was empty and had no custom properties. The configured-default
template's file identity is unavailable. Save, close, reopen and resave precede
capture; actual document handles are retained from producer responses. Exports
preserved geometry, configuration, semantic revision and native update stamp.
Only this capture's documents were closed.

| Artifact | Bytes | Effective units/version |
| --- | ---: | --- |
| Native SLDPRT | 57,843 | SolidWorks 2025 SP5; reopened and measured |
| Parasolid binary | 10,599 | metre; 36.01.228 |
| Parasolid text | 11,266 | metre; 36.01.228 |
| STEP | 24,958 | millimetre; ISO-10303-21, AP214 |

All artifact hashes and sizes match producer receipts. Reference exports contain
both bodies. Native measurements and geometry evaluation use each body's own
native reference; reference handles and XT node IDs remain separate namespaces.

## Independent expectations

Each block has six planar faces, twelve straight edges, eight vertices and one
connected shell. The complete part has twelve faces, twenty-four edges, sixteen
vertices and two connected shells. Each body has 90 native curve/surface
samples, checked against its own bounds, plane equations, straight curves, trim
membership and outward material normals.

| Quantity | Large block | Small block | Whole document |
| --- | ---: | ---: | ---: |
| Volume, mm^3 | 24,000 | 3,000 | 27,000 |
| Boundary area, mm^2 | 5,200 | 1,300 | 6,500 |
| Geometric centroid, mm | (10,15,20) | (55,7.5,10) | (15,14.1666666667,18.8888888889) |

The admission contract checks each body's measures and centroid independently,
then verifies document totals and the volume-weighted centroid. Equal or
compensating total measures cannot replace per-body checks. The schema supports
either the existing singular `selection.body_id` or `selection.bodies`, never
both. Multiple selections must map unique IDs to every observed native body key
exactly once. This is a case-specific, reviewed mapping, not an automatic matcher
in the Parasolid reader.

## Reader and STEP evidence

The embedded partition contains 331 decoded nodes, including twenty-four line,
twelve plane and sixteen point geometries. Its model has no reference or
geometry issues. The delta contains 65 delta nodes in four packets; the two
ordinary schema nodes are counted separately. Both streams decode completely,
with no uninterpreted bytes. Partition 0 and both selected bodies pass topology
and geometry binding without interval overrides.

The existing exporter API exports one explicitly selected body per call. The
runner calls it for BODY 6 and BODY 2, writing separate STEP files. Each output
must contain exactly one complete solid with its source faces and edges. No
library code changes or combined multi-body STEP API were needed for this case.

The independent OCCT checker verifies positioned corners, edge connectivity,
plane positions and outward normals. It uniquely maps both native reference
solids by geometry, independently of native STEP ordering. Each selected output
has zero bidirectional difference volume against its corresponding native
solid. Combining the two outputs in the validator also gives zero difference
against the entire native reference, with both solids retained.

Negative kernel tests reject swapped selections, duplicate exports, a missing
export, a duplicate native body, a selected export containing both bodies and a
shifted small block despite unchanged volume and area. Reversed native body
ordering is accepted. The live library replay additionally selects non-BODY node
1: the API must report the wrong node type and write no STEP file.

The [existing limits](known_limits.md) remain: explicit checkpoint verification
is not automatic history reconstruction. Standalone native `.x_b` ASCII headers
and `.x_t` text grammar are not supported by the binary reader.

## Repeat

Use the [shared runner](block_capture.md#repeat-an-admitted-starter-case) and a
new output directory:

```sh
.venv/bin/python tools/run_case.py \
  --case part-multiple-solids-001 \
  --openswx-build /absolute/path/to/openswx/build \
  --exporter /tmp/openswx-corpus-build/case_export \
  --occt-python /tmp/openswx-corpus-occt/bin/python \
  --output results/multiple-solids-run-001
```

The report records both explicit selections and separate export statistics.
Topology and binding stages pass only after both bodies pass. The STEP stage
requires both per-body and whole-part equivalence, plus invalid-selection
rejection. The existing one-body runner reports retain their original structure.
