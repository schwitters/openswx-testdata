# Original perpendicular cylinder cross-bore

This original MIT coupon was constructed through SolidWorks MCP on SolidWorks
2025 SP5, without importing private geometry. A centred radius-26 mm cylinder
is extruded 20 mm symmetrically about its sketch plane. A centred radius-4 mm
circle on a perpendicular standard plane cuts through it with an 80 mm
symmetric extrusion. Native captures, requests, receipts and hashes are frozen
in `manifest.json`. Only the owned synthetic document was closed; authentication
headers are absent from the journal.

The saved source contains one solid with four faces, four edges, eight loops
and no source vertices. Two supporting planes, two cylinders, two circles and
two direct intersection curves are typed and bound successfully. The native
B-rep query independently reports those counts. The two intersection branches
are not circles: the two cylinder axes are perpendicular. The current exact
STEP path rejects this whole body with `Intersection circle requires a planar
support` and creates no partial STEP file. Successful binding is therefore not
an exporter success or a saved-state membership certificate.

The reference STEP imports as a valid solid with four faces, six edges and
four vertices. OCCT adds two linear cylinder seams. SolidWorks serializes each
non-circular intersection as a nonrational cubic B-spline with 65 controls.
An independent integral of the two cylinder equations gives volume
39868.283790038855 mm³ and area 8712.993291789462 mm². The native STEP measures
39868.28694839344 mm³ and 8712.993664186211 mm². That observed approximation is
recorded explicitly; it does not change OpenSWX's length tolerance or certify
an approximate replacement curve. The future exporter extension must specify
its representation and error contract instead of fitting a circle to chart
points or treating the native reference as mathematically exact.

`cross-bore.x_b` is the immutable native Parasolid export including its standard
text preamble. `source-inspection.json` describes the binary partition extracted
from `cross-bore.sldprt`; the inspector CLI accepts extracted `PS\0\0` streams,
not an unstripped native export preamble.

Run the evidence and optional OCCT checks with:

```sh
python -m unittest discover -s tests -p test_native_cross_bore.py -v
```

Set `OPENSWX_CORPUS_BUILD` to the code build directory to also verify live saved
source extraction and binding. Set `OPENSWX_CORPUS_EXPORTER` to the compiled
`tools/case_export.cc` driver to check the explicit whole-body rejection and
absence of partial output. This driver now optionally accepts both
`OPENSWX_CORPUS_INTERSECTION_CHART_TOLERANCE` and
`OPENSWX_CORPUS_INTERSECTION_SOLVE_TOLERANCE`; both must be positive finite
numbers when either is supplied. Other captures retain their original defaults.
