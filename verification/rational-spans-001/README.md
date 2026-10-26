# Rational spline with a simple interior knot

Original MIT construction made through SolidWorks MCP, SolidWorks 2025 SP5.
No imported or confidential geometry was used. `recipe.json` and `journal.json`
record the construction, native B-rep query, save/export receipts and closure
of the owned document. Authentication headers and artifact-download responses
are excluded. Both document and configuration properties are empty.

The 8 mm prism has a rational cubic lower profile with five weighted controls,
knots [0, 0.4, 1] and multiplicities [4, 1, 4]. An independent rectangular
through cut removes x < 3 mm. Native B_CURVEs retain their complete source
[0,1] domain, five original homogeneous controls and the simple interior knot;
actual edge intervals start at approximately 0.22075694269923174 and end at 1.
The remaining edge crosses the interior knot, so complete-domain or
piecewise-Bezier-only recovery cannot substitute for this regression.

At code commit 9c87f49 the exact driver rejected BODY 2, face 41 with
`Spline inversion requires a certified monotone projection` and produced no
STEP output. The current proof evaluates each original knot span's blossom in
outward-rounded homogeneous interval arithmetic, certifies the full positive
weighted derivative numerator, and subdivides only proof coefficients where
needed. Neither source geometry nor parameter units nor caller tolerance is
changed. The certificate is shared by partial edge binding and swept-surface
inversion. It does not cover periodic/unclamped curves or arbitrary NURBS faces.

The complete current export has one solid, five faces, nine edges and six
vertices. Native and current STEP have identical measured volume and area,
and zero two-way Boolean solid differences. `tests/test_rational_spans.py`
independently evaluates the recipe's rational B-spline basis/derivative and
integrates planar area, profile length, prism area and volume across the knot.
It verifies source extraction, both partial edges, unchanged knot/weight data,
complete export, capture integrity and document closure. Native measurements,
the previous rejection and the analytic oracle are frozen separately in JSON.

Set `OPENSWX_CORPUS_BUILD` and `OPENSWX_CORPUS_EXPORTER` to run live library
checks. Optional OCP checks native/current STEP validity, topology, geometry and
solid differences. Selection is explicit payload 0 / BODY 2; successful export
alone makes no assertion about general saved-state/body membership.
