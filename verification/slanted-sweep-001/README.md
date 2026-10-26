# Exact plane/swept intersection and variable-height strip

Original MIT construction created through the SolidWorks 2025 SP5 MCP server.
No imported or confidential geometry was used. An 8-to-11 mm slanted upper
plane clips a 14 mm extrusion of the cubic profile X=12t, Y=9t³ (millimetres),
with a horizontal closing edge at Y=9. The complete final body has five faces,
nine edges and six vertices. The saved source retains one direct INTERSECTION
between a PLANE and SWEPT_SURF, one polynomial lower B_CURVE and two straight
generators. Its reader binding already succeeds with the explicit settings in
`expected.json`; the former exact exporter rejected the non-ring intersection.

The new writer derives the upper cubic Q(t)=(12t,9t³,8+3t) directly from the
original supporting plane and swept section. Four original-degree controls
represent the entire intersection. Outward control arithmetic certifies
construction error; global chord projections isolate the chart branch and
condition endpoint uncertainty. No chart-point fitting is performed. Source
geometry, topology, chart parameters and caller tolerance remain unchanged.
Writer-local intervals use the section's natural parameter. Positive whole-
profile gap coefficients certify the variable parameter strip; its exact
polynomial Bernstein-product flux has outward error bounds. A finite tensor
support covers the strip while the original trim edges bound the actual face.

Independent integration gives volume 745.2 mm³ and surface area
508.8273370016069 mm². The current export matches these values within the
recorded verification limits and imports as a valid complete solid in OCC.
The native STEP is an approximate reference: its upper cubic has 22 controls,
a sampled equation residual of about 0.0001952 mm, a volume discrepancy of
about 0.00009572 mm³ and an area discrepancy of about 0.00007312 mm².
These observed differences are frozen in `occt.json`. OCC's two solid
subtractions return zero under its imported tolerances; that alone does not
prove exact equality. Native reference differences never relax the library's
length tolerance. The analytic recipe and derived coefficients are independent
oracles; curve samples are diagnostic only.

Native SLDPRT, Parasolid and STEP bytes, receipts, empty property queries and
creation/export/close responses are retained. Header-free journal entries also
record safely rejected not-ready retries (outcome_unknown=false); exactly one
owned-document close completed. Download responses are excluded and artifact
hashes verified. Explicit payload 0 / BODY 2 selection does not establish a
general saved-state reconstruction or body-membership rule.

Run `tests/test_slanted_sweep.py`. Configure `OPENSWX_CORPUS_BUILD` and
`OPENSWX_CORPUS_EXPORTER` for live extraction, binding and complete export;
optional OCP verifies topology, analytic measures and the native observations.
Rational/multispan variable strips, general curved intersections, closed or
multiply trimmed sweep regions and trim-wrapper recovery remain separate work.
