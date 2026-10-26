# Tolerant cylinder / rational carrier mapping

Original MIT construction, created through the SolidWorks 2025 SP5 MCP server.
The native sheet is a quarter-cylinder, radius 10 mm and height 20 mm, defined
by the rational tensor product in `recipe.json`. Its independent area is
100*pi mm². Native STEP/Parasolid and SLDPRT bytes, SHA receipts, empty property
queries and the creation/export/close journal are retained. Authentication
headers and download responses are excluded from the journal.

The C++ fixture `libopenswstep/tests/tolerant_cylinder_fixture.h` constructs
the tolerant topology separately: two opposite affine pcurves, a 0.3 µm
interior bow on the rational carrier, and a stored plane-intersection master
whose chart extends beyond the selected edge. Its source edge allowance is
2 µm; strict 0.1 µm recovery must reject it. No native tolerant topology is
claimed: SolidWorks supplies an independent exact circular carrier reference.
Tests also cover no master, an existing circle master, invalid orientation,
wrong trim/plane/reference, nonconstant height, closed axes and finite budgets.

`openswstep_tolerant_cylinder_fixture` exports the certified shared curve as
an isolated STEP wire. `tests/test_tolerant_cylinder.py` checks that wire against
the native sheet using OCC distance and analytic length checks. An additional
OCC z=0 section check has a 2e-6 mm length allowance: OCC's approximated
section differs from the analytic quarter-circle by about 1.63e-6 mm. Direct
recovered-curve distances to the native sheet must stay below 1e-8 mm; this
independent reference allowance never changes library acceptance tolerances. This checks the recovered curve, not whole B_SURF face serialization,
original paired PCURVE serialization or whole-spring export. The unit test
checks that both original pcurve arrays are retained by the recovery result.
Private spring geometry and its derived exports are not present.

Run with `OPENSWX_CORPUS_TOLERANT_FIXTURES` pointing to that executable and a
Python environment containing OCP. The native source is an original surface
coupon; its internal payload does not establish saved-state/body membership.

The native SLDPRT embedded payload 0 binds BODY 1 completely at 1e-8 m
(one face, four edges and four vertices; one rational B_SURF and four B_CURVEs).
Its isolated stream has twelve missing `next` reference targets; the inspector
therefore exits 2 while emitting complete body binding. The live regression
requires exactly those diagnostics, zero invalid/unsupported geometry, and the
recorded body counts. No saved-state or final-body membership claim follows.
