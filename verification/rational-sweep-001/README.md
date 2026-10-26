# Exact rational sweep STEP export

This verification extends the original MIT native coupon captured in
`../rational-trim-001`. No source or native reference bytes were changed or
recaptured: `expected.json` pins both SHA-256 values. The previous fixture's
frozen README/expectations document its historical unsupported STEP result;
this directory records the current successful contract.

The complete clipped rational cubic prism exports with all five faces, nine
edges, six vertices and one solid. The mantling surface uses an exact rational
tensor product: the exactly restricted homogeneous profile weights appear at both ends of
the linear extrusion axis. Exact knot insertion derives the restricted controls
and weights in original knot units. The source Model and selected trim edges
remain unchanged; no curve or surface is fitted. Native and library STEP pass OCC validity checks and
have zero solid difference in both directions. Independent rational-polynomial
volume/area oracles from the original coupon still apply.

Rational planar cap area and swept flux are checked with outward-rounded
Bernstein quotient enclosures, refined six levels with finite shared work.
Their uncertainties enter the signed-volume certificate. These bounds only
validate the result; they do not replace or fit any exported geometry. A shell
whose positive volume cannot be certified is rejected. The subset requires
open quadratic/cubic profiles, two corresponding translated curves with
identical weights, two straight generators and one rectangular parameter
region. Rational planar caps require a certified convex control polygon.
General rational B_SURF trims, periodic surfaces, additional loops and differently
weighted profile representations remain unsupported.

`tests/test_native_rational_trim.py` exercises live current support when
`OPENSWX_CORPUS_BUILD` and `OPENSWX_CORPUS_EXPORTER` are configured. Optional
cadquery-ocp checks the entire current export against the native reference.
The original native construction journal, receipts and empty-property checks
remain in the earlier fixture. Private spring geometry or its exports are not
part of either fixture.
