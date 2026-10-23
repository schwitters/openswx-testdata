# First SolidWorks 2025 capture

## Entry conditions

Start with `part-block-001`, `part-cylinder-001`, then `part-tube-001`. They
exercise planar faces, periodic cylindrical surfaces, holes and closed shells
without requiring advanced construction tools. Their recipes and analytic
checks are already present. P0 means capture priority, not an assertion that
every runtime capability is currently available.

Before mutating a document:

1. Read the actual MCP tool schemas and effective runtime capabilities.
2. Record SolidWorks year/build/service pack, worker version, capability response
   and effective export support. The target is 2025; do not silently accept a
   different producer. A later build is a separate recorded producer variant.
3. Confirm original, corpus-owned templates, an isolated artifact directory,
   export scope, resolved units and verified versions. AP214 is the first STEP
   reference protocol. Do not use an active user's document or UI selection.
4. Map the semantic starter operations to the advertised command envelopes.
   Validate requests through the backend's validation mode when available.
5. Reject missing required capabilities before construction. Do not replace a
   requested spline or surface with an approximate sketch.

## Transaction for each independent case

1. Create a fresh document from the corpus-owned template. Give the run a unique
   operation namespace and isolated staging directory. Reuse an operation ID
   only for a retry of the same payload under the server's replay contract.
2. Execute the recipe in order, resolving semantic step IDs to returned native
   references. A failed operation ends this run. Keep failure evidence; do not
   continue from an uncertain partially modified document.
3. Rebuild and read back the result. Require exactly one solid body for each
   starter recipe, with native area and volume matching the analytic model.
4. Save the native file. Close and reopen it using the returned artifact path.
   Select the intended configuration, rebuild if needed, and establish the
   revision used by all subsequent observations and exports. Re-save if reopening
   changes the persisted state, then repeat until the captured state is stable.
5. Query native measurements and, where available, B-rep and geometry samples.
   Normalize documented API measurement units to SI, retaining original units
   and readbacks. Missing detailed queries are explicitly unavailable, not zero.
6. Export whole-document binary Parasolid, text Parasolid and STEP AP214 from
   that state. Require verified receipts with actual units, versions, revision,
   configuration, scope, sizes and SHA-256. Geometry readback before/after export
   must agree. An export that changes the document state invalidates the capture.
7. Retrieve complete artifacts and verify each receipt against local bytes.
   Native `.sldprt` and all reference exports must be readable by the relevant
   native reader; an integrity audit alone cannot establish format validity.
8. Build the normalized native snapshot and `case.json` using the supplied
   schemas. Review per-stage expectations rather than inferring them from a
   successful save. Use explicit known-unsupported codes/issues for gaps.
9. Audit the complete staged candidate in a temporary corpus checkout. Run the
   three library stages and independent STEP verification described in the
   regression contract. Record observations separately from expectations.
10. Admit the case under `cases/<id>/` only with reviewed provenance and results.
    Commit source files, native snapshots, reference exports and receipts
    together. Preserve failed generation attempts outside admitted cases.

A repeated run should reproduce construction intent, body kind and geometric
measures. It need not reproduce timestamps, file hashes or stream-local IDs.

## Starter analytic expectations

All recipe dimensions are metres. Full external and internal boundary area is
included; these are not projected areas.

| Shape | Volume | Boundary area |
| --- | --- | --- |
| Block, sides `w,d,h` | `w*d*h` | `2*(w*d+w*h+d*h)` |
| Cylinder, radius `r`, height `h` | `pi*r*r*h` | `2*pi*r*r+2*pi*r*h` |
| Tube, outer/inner radius `R,r`, height `h` | `pi*(R*R-r*r)*h` | `2*pi*(R*R-r*r)+2*pi*(R+r)*h` |

Choose finite positive tolerances from source/kernel accuracy and minimum feature
size. Review absolute and relative terms separately; do not enlarge tolerances
automatically until a case passes. Approximate native bounding boxes are useful
observations, not exact geometric certificates.

## Subsequent batches

1. Finish P0 extrusions/cuts and multiple-body selection.
2. Add detailed native B-rep/evaluation capture, actual geometry-family inventory
   and P1 curved geometry. Prioritize NURBS surfaces and plane/cone intersections.
3. Add translated, rotated and scaled variants and verify the corresponding
   geometric relations, including volume scaling by `s^3` and area by `s^2`.
4. Add configurations and saved/reopened history sequences with separately known
   final snapshots. Record actual base/delta occurrences; editing does not
   guarantee the presence of a delta stream.
5. Add self-contained assemblies and drawings, using relative dependency paths
   and corpus-owned templates. Extend schemas and capture tests before admitting
   those document kinds.
