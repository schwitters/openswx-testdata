# Rational plane/swept intersection, graph strip and exact UV curves

Original MIT construction made through SolidWorks 2025 SP5 MCP. The sketch has
Cartesian cubic controls (0,0), (4,0), (8,0), (12,9) mm with weights
[1,0.75,1.25,1]. A 14 mm extrusion is clipped at z=8+0.25*x mm. No imported
or confidential geometry was used. Native SLDPRT, Parasolid and STEP bytes,
receipts, header-free construction/export/close responses and empty property
checks are retained. The single owned document was closed successfully.

The selected source partition contains one five-face solid with nine edges
and six vertices, one rational SWEPT_SURF section and a direct plane
INTERSECTION. Both original B_CURVE arrays retain the original weights.
The previous exporter at b3dbf31 rejected this rational intersection. The new
homogeneous plane map preserves the source 3D degree, weights, knots and model;
writer-local curves use the source section's parameters. Whole rational
weighted-derivative bounds certify chart direction and conditioned endpoint
uncertainty. Identical positive profile weights and positive height ordinates
certify the entire strip. Its W^-3 surface flux has outward integral bounds.

Rational UV curves are essential here. Deriving missing pcurves in the local
OCC importer produced about 0.00006812 mm of edge/surface disagreement in a
development diagnostic. The library now writes explicit SURFACE_CURVE/PCURVE
representations. The homogeneous u*W numerator raises UV degree to four while
the 3D degree stays three. Source coordinates and weights remain unchanged;
new UV weights are normalized and degree-elevated algebraically. Outward
perturbation bounds lift UV rounding into the unchanged 3D length allowance.
The finite surface is cached by face identity so its PCURVE and ADVANCED_FACE
refer to the same surface instance, including separate trims of one support.

Independent rational-polynomial integration gives volume
761.0124313550398 mm³ and area 513.7784286656572 mm². The current complete STEP
matches within 1e-6 in those measure units and has sampled edge/surface
coherence below 1e-10 mm. Curve samples are diagnostics; control and derivative
bounds establish the mathematical mapping. OCC area integration is sensitive
to its requested accuracy: tests sum per-face results at Eps=1e-14; default
1e-12 readouts are retained separately in occt.json. No library tolerance is
increased. Native STEP is an approximate reference and its volume/coherence
errors are recorded independently instead of becoming acceptance thresholds.

`tests/test_rational_strip.py` verifies capture integrity, original weights,
complete source binding, explicit rational pcurves and whole-body analytic
measures. Set OPENSWX_CORPUS_BUILD and OPENSWX_CORPUS_EXPORTER for live checks;
OCP is optional. The code-only RationalVariableWedge fixture also tests a
curved rational implicit cut through public export, with a closed-form volume
and optional independent OCC round trip. It requires no native artifact.

This subset still requires one open clamped quadratic/cubic source span and
matching profile bases and weights. Multispan/closed/multiply trimmed strips,
proportional but differently stored weight arrays, trim-wrapper recovery and
general NURBS intersections remain separate work. Explicit payload 0/BODY 2
selection is not a general saved-state membership certificate.
