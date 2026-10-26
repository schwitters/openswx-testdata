# Original native analytic cuts

Three original MIT models were constructed through SolidWorks 2025 SP5 MCP,
without imported or private geometry. Native SLDPRT, AP214 STEP, binary/text
Parasolid, artifact receipts, empty property checks and the authenticated-call
journal (without authentication headers) are frozen by `manifest.json`. All
three owned documents were closed. These additional verification fixtures do
not alter the original nineteen-case capture history.

| Case | Construction in millimetres | Oracle |
| --- | --- | --- |
| `torus-minor` | Circle centered 20 from the Z axis, radius 4, revolved 90° | Volume 160π² mm³ |
| `torus-major` | Same circle revolved 270° | Volume 480π² mm³ |
| `sphere` | Radius 5, center (10,20,30), cap above height 3 along (0,0.6,0.8) | Area 20π mm² |

Both native torus partitions contain BODY 2 and three faces. Their two complete
meridian cuts have normals perpendicular to the torus axis. Baseline openswx
4f935ba rejected both with `Torus cut circle is tilted or degenerate`.
The new meridian certificate retains the source circles, chooses the small or
large sector from winding, and exports every face. Both native STEP references
and both equivalent C++ fixtures pass OCCT validation; their bidirectional
solid differences are zero. Importers add a periodic seam: two source edges
become three OCCT edges. Torus area is 2πRrθ + 2πr².

The native sphere SLDPRT stores its polar frame along the cut normal and was
already exportable at baseline. It is an independent reference for the C++
`sphere-oblique-sheet-native` fixture, which preserves exactly that sphere and
cut but stores the global Z polar axis. This distinction is intentional: the
capture alone does not reproduce the old SPHERE pole-frame restriction.
The equivalent-frame test checks the native sphere and 3D circle supports,
analytic output area and bidirectional **surface-area** differences. A volume
comparison would provide no useful evidence for this open sheet.

The native AP214 sphere frame is rotated again, to (0,0.8,-0.6). OCCT's native
trim integration returns 62.833706522374165 mm², about 0.00185345 mm² above the
exact 20π; the analytic library STEP returns 20π. This frozen native STEP
integration observation is checked separately, with a 0.002 mm² bound for this
reference only. It does not change source tolerances or the analytic output
oracle. Native and output cuts retain the same exact 3D circle and sphere;
bidirectional Boolean sheet differences have zero area. No volume criterion is used for this sheet.

The sphere's BODY 1 is in embedded FeatureBodies storage; its configuration
partition is empty. Explicit payload selection is justified here by the original
one-body construction, not by a new general resolver rule. Its frozen inspection
also reports 13 missing attribute-chain `next` references; geometry is complete
and body binding succeeds. This is not a claim of complete metadata resolution.
Negative-major-radius tori, noncoaxial sphere cuts, partial meridian cuts and
arbitrary analytic trimming remain outside this feature. Text Parasolid is
retained as reference input, not a text-decoder support claim.

Run `python -m unittest discover -s tests -p test_native_analytic_cuts.py -v`.
Optional `cadquery-ocp` enables geometry checks. Set `OPENSWX_CORPUS_BUILD` and
`OPENSWX_CORPUS_EXPORTER` as for the other native regression tests to verify
current extraction and native body export. Set
`OPENSWX_CORPUS_ROUNDTRIP_FIXTURES` to the built
`openswstep_roundtrip_fixtures` executable to compare the equivalent C++ source
frames against the native references, including the deliberately oblique sphere.
