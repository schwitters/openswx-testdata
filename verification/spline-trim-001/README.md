# Original native partial B-spline trims

Two original MIT parts were constructed through SolidWorks MCP on SolidWorks
2025 SP5. Each starts from a cubic sketch and its two straight closing lines,
is extruded 8 mm, and is cut through by an independently sketched rectangle.
No private or imported geometry was used. Native SLDPRT, binary/text Parasolid,
STEP, immutable receipts and the authentication-header-free MCP journal are
frozen in `manifest.json`. Both owned documents, including their later text
export reopenings, were closed. Document and configuration custom properties
were checked empty.

The constructions address two reader boundaries:

| Case | Source profile in millimetres | Ideal remaining parameter interval |
| --- | --- | --- |
| `cubic` | x(u)=12u, y(u)=9u³, closed at y=9 | [5/12,1] |
| `reversal` | x(u)=30u−33u²+23u³, y(u)=12u−9u²+7u³, closed at y=10 | [1/2,1] |

The native saved B_CURVEs retain their complete `[0,1]` knot domain and four
original controls. Each edge only uses the remaining partial interval. The
second profile has projected derivative Bernstein controls [720,−30,810] along
its endpoint chord, yet its actual quadratic derivative is positive everywhere:
720−1500u+1590u² has a positive global minimum. A negative control alone is not
a proof that the curve folds. This distinguishes a bounded derivative
certificate from simply accepting every nonmonotone control polygon.

Native Boolean vertex rounding is retained, rather than snapped to the ideal
recipe: the second captured recovered trim starts at 0.5000000001534081.
`expected_recovered_parameter` records that reader observation separately from
the ideal analytic cut. The native B-rep query independently reports a very
close trim parameter; both refer to the same saved geometry within native
numerical precision. Source controls, knot units and caller tolerances remain
unchanged. The old library baseline rejected both cases with `Spline domain
endpoints need unambiguous vertex correspondence`; those historical failures
are preserved separately from the new successful expectations.

Both complete exports contain five faces, nine edges, six vertices and one
solid. Independent polynomial integrals give ideal volumes 28273/96 mm³ and
17017/80 mm³. An independent arc-length integral supplies surface-area oracles.
Native and library STEP imports pass OCCT B-rep validation and both Boolean
differences are zero. Their small numerical volume/area residuals against the
ideal recipe are frozen in `occt.json`; tests keep a 1e-6 mm³/mm² oracle bound,
separate from the unchanged 1e-8 metre binding tolerance. Tests also inspect the
exported cubic edge basis, original parameter interval and polynomial geometry.

The `.x_b` references retain their native export preambles. The live reader
test extracts binary partitions from SLDPRT. The paired native `.x_t` references
provide reproducible future text-decoder input; the current inspector must
still reject text explicitly. They are not a claim of text parsing support.

Run the evidence and optional OCCT checks with:

```sh
python -m unittest discover -s tests -p test_native_spline_trims.py -v
```

Set `OPENSWX_CORPUS_BUILD` to the library build and
`OPENSWX_CORPUS_EXPORTER` to the compiled `tools/case_export.cc` driver to also
exercise current extraction, automatic body binding, whole-body STEP export,
original cubic curves, independent measures and native Boolean comparisons.
Rational, periodic, unclamped, SP and uncertified partial curve recovery remain
separate work items; these parts do not establish general spline inversion.
