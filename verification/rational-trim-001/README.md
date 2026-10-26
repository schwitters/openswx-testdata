# Original native rational partial-domain coupon

An original MIT SolidWorks 2025 SP5 part was constructed through MCP from a
rational cubic sketch, extruded 8 mm, then cut through at x=5 mm. It is unrelated
to any confidential spring model. Cartesian profile controls in millimetres
are (0,0), (4,0), (8,0), (12,9), with weights [1,0.75,1.25,1]. The other two
profile lines close at y=9. Native SLDPRT, STEP and binary/text Parasolid, native
B-rep observations, artifact receipts and the header-free request journal are
frozen by SHA-256. The owned document was closed and document/configuration
custom properties were checked empty.

The complete rational profile remains in its original [0,1] domain, while each
retained edge starts near 0.390189994608039. The homogeneous polynomials are:

- X(u) = 9u + 12u² − 9u³ mm
- Y(u) = 9u³ mm
- W(u) = 1 − 0.75u + 2.25u² − 1.5u³

Independent tests solve X−5W=0 and integrate (9−Y/W) d(X/W) for section area,
plus rational arc length for surface area. The native STEP passes OCCT topology
validation; its two retained rational cubic edges match these polynomials.
Baseline openswx 9bf7caa rejected automatic partial rational edge binding.
The new positive weighted-derivative certificate binds all five faces, nine
edges and six vertices without changing controls, weights, knots or tolerance.
The certificate is also reused for rational SWEPT_SURF inversion.

**Whole-body STEP export remains unsupported** at the polynomial-only sweep
certificate. Tests require this explicit error and absence of a partial output;
they do not claim that successful binding displays a spring or supports general
rational B_SURF trims. Separate original C++ spatial rational curves cover two
XY turns with increasing Z. They are not exact constant-pitch helices and are
not derived from private CAD. The `.x_t` artifact is a future decoder reference,
not a text-reading support claim.

Run `python -m unittest discover -s tests -p test_native_rational_trim.py -v`.
Optional cadquery-ocp enables native geometric checks. `OPENSWX_CORPUS_BUILD`
and `OPENSWX_CORPUS_EXPORTER` enable current extraction, complete binding and
the remaining STEP failure check, as in the other native regression fixtures.
