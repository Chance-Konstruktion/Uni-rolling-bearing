# Engineering audit – UNI Rolling Bearing Generator

**Audit date:** 2026-10-26  
**Scope:** static source review of the default-branch snapshot used as the PR base, followed by targeted edits and regression-test additions on the audit branch.  
**Status:** implementation changes are in this PR; final CI confirmation and CAD-host integration remain release gates.

## Executive summary

The project has a useful separation between a host-free geometry core and Blender/FreeCAD frontends. The codebase is not yet proven to be a certified or fully standards-conformant bearing design tool. A successful host-free test suite can demonstrate software invariants, but does not independently validate the bearing formulas, every catalogue dimension, mesh manifoldness, OpenCascade topology, or real STEP round-trips.

This PR prioritizes reproducible defects and unsafe failure modes over adding new bearing families.

## Scope reviewed

- Geometry resolution, pitch-circle element placement and auto-fit behavior: `geometry.py`, `raceway.py`, `constants.py`.
- Load ratings, equivalent load, nominal life, fit recommendations and dimensional tolerance windows: `ratings.py`, `fits.py`, `tolerances.py`, `din623.py`.
- Built-in JSON catalogues and validation/loading of optional user catalogue data: `norm_engine.py`, `uni_rolling_bearing/data/*.json`.
- FreeCAD build plan, Part backend, workbench analysis and Blender ratings panel.
- Existing unit tests, CI workflow, and the shipped Blender ZIP packaging check.
- Existing roadmap and changelog, to distinguish implemented functionality from unverified claims.

## Findings and changes in this PR

### 1. Circumferential element count used arc length instead of chord distance

The previous count limit divided the pitch-circle circumference by a nominal element pitch. That checks arc length, but adjacent element centres are separated by a chord. At high fill ratios, this could permit adjacent balls or rollers to overlap.

**Change:** `max_elements_for_pitch()` uses the chord relation (s_N = d_m \sin(\pi/N)), handles invalid/non-finite inputs, and no longer forces an impossible arrangement to at least three elements. The resolver now reports when the requested geometry cannot fit the minimum element count. Suggested defaults are capped to a feasible three-element spacing.

**Regression coverage:** chord-boundary, impossible count, and invalid geometry cases were added to `tests/test_geometry.py`.

**Bounded resource use:** the maximum supported count is capped at 256, matching the Blender UI limit. This also prevents extreme but finite diameter ratios from generating impractically large meshes.

### 2. Pure axial load in the tapered-bearing calculation

For a tapered bearing with positive contact angle and (F_r=0), the previous branch returned an equivalent load of zero. That could suppress the nominal-life result despite a nonzero axial load.

**Change:** the existing simplified equivalent-load model now contributes (P=YF_a) in this special case. A dedicated regression case checks the nonzero equivalent load.

**Limit:** the model's coefficients and applicability still require comparison with authoritative, legally usable reference material and manufacturer data. This fix does not certify the complete rating model.

### 3. Spherical-bearing contact angle and analysis/build parity

The rating helper always used 10° for spherical bearings, ignoring the configurable UI parameter. The FreeCAD analysis readout also resolved nominal rather than tolerance-adjusted dimensions and did not apply the same two-row rolling-element-length reduction as the build plan.

**Change:** the shared ratings helper honours the passed spherical contact angle; Blender and FreeCAD readouts pass the configured angle. FreeCAD analysis now uses effective dimensions after the selected tolerance position and matches the two-row length adjustment used by the plan.

**Regression coverage:** tests target angle-dependent load factors and the displayed pitch-circle parity between analysis and the FreeCAD build plan.

### 4. Invalid numerical geometry inputs

The geometry resolver previously relied on comparisons that do not reliably reject NaN, infinity, negative clearances, unsupported bearing-type IDs, or malformed element counts. It could also force a minimum count after the geometry had become infeasible.

**Change:** finite-number, type, positive-dimension, clearance, gap-factor, conformity, angle, element-count and auto-fit checks were added. Impossible roller/count combinations return an explanatory error instead of a fabricated valid-looking plan.

**Regression coverage:** tests cover NaN/infinity, non-positive dimensions, malformed counts, unsupported types, invalid clearance/gap/angle and infeasible spacing.

The shared specialised-option validator also checks V/U groove shape and angle, chamfers, tapered-ring dimensions, mesh resolution, cage type/material, and cage/oil-pocket clearances. The Blender resolver, FreeCAD plan, and FreeCAD analysis all use this check.

### 5. Malformed catalogue overrides and tolerance/fit selections

The norm loader converted custom catalogue values to floats without consistently rejecting NaN, infinity, non-positive dimensions, or (D \le d). Unknown tolerance classes silently fell back to NORMAL; unknown tolerance positions silently fell back to MEAN. An unknown fit load case could fall through to the heavy-load branch.

**Change:** direct and DIN-style preset payloads are type-checked and filtered for finite, positive, dimensionally ordered values. Malformed user payload structures are ignored safely. Tolerance classes, positions, and fit load cases now reject unknown values with actionable `ValueError` messages; the FreeCAD analysis panel converts invalid fit inputs into a visible message.

Tolerances beyond the compact table's 250 mm upper limit now fail explicitly instead of silently reusing the final row. Non-string class/load-case values are also rejected safely. Rating entry points reject NaN/Inf and malformed counts/row settings; the FreeCAD analysis panel displays invalid load/speed settings rather than reporting a fabricated result.

**Catalogue sanity check:** a static audit counted 196 built-in catalogue entries across the six data files. All passed basic finite/positive-dimension checks and (D>d). This is a structural plausibility check only, not independent verification of the dimensions against published catalogue tables.

### 6. FreeCAD cage boolean failures were silently ignored

The FreeCAD backend caught exceptions from individual pocket booleans and continued, potentially returning a cage with missing pockets.

**Change:** a failed, null, or invalid boolean result now raises an actionable error containing the pocket index and advises checking geometry or selecting the LADDER cage. A host-free regression test simulates a failed boolean to ensure the failure is not silently swallowed.

**Limit:** the actual OpenCascade operation and all supported FreeCAD releases still need real-host tests.

The workbench now exposes a read-only `BuildError` status, migrated onto existing saved bearing objects. A failed rebuild leaves the last successful Shape in place but labels it as stale; successful rebuilds clear the status. The Part backend also checks returned rings, rolling elements, cage parts and the final compound for empty/invalid shapes when FreeCAD exposes those checks. Host mocks verify the failure path, but they cannot certify actual BREP validity.

### 7. Shipped Blender ZIP was stale

An earlier CI run on this PR passed syntax compilation and the then-current unit tests but failed the ZIP/source synchronization check. The six updated package modules have since been copied into the ZIP and the archive directory, file sizes and CRCs checked by a dedicated script before the updated blob was committed.

**Gate:** the repository's own `python build_addon_zip.py --check` CI step must pass on the final PR head. The manual archive check is not a substitute for that CI result.

## Verification status

The completed GitHub Actions run **#93** on commit `681b97f7477f37ac52c35c896f5c83e89ef33991` passed the full matrix on Python 3.10, 3.11 and 3.12. Each interpreter ran **279 host-free unit tests successfully**, passed syntax compilation, and passed `python build_addon_zip.py --check`. The shipped Blender ZIP has been synchronized with all seven changed package modules.

### Done in code / tests added
- Geometry element spacing based on chord distance, with a hard supported-count cap of 256.
- Regression cases for pure axial tapered load and configured spherical contact angle.
- Host-free validation for geometry, rating inputs, specialised raceway/cage options, fits, tolerances and catalogue parsing.
- Explicit errors for bearing dimensions outside the supported tolerance table (over 250 mm), instead of silent extrapolation.
- Consistent effective dimensions and two-row length in the FreeCAD analysis readout.
- Visible failure for unsuccessful FreeCAD booleans, validation of resulting CAD solids, and a read-only FreeCAD rebuild-error property that also migrates onto existing documents.
- Basic structural sanity checks across all 196 built-in catalogue entries.
- Shipped Blender ZIP synchronized; automated packaging parity passed in CI.

### Still open; do not treat as verified
- Install/run Blender and FreeCAD in actual supported host versions.
- Inspect all six bearing types for valid/manifold meshes, normals, self-intersections and dimensional bounds at coarse and fine resolutions.
- Check FreeCAD `Shape.isValid()`, solid counts, volumes and bounding boxes for all supported types/styles.
- Export and re-import representative STEP files and compare shape/volume/bounds.
- Verify each catalogue dimension against a trustworthy manufacturer catalogue or authoritative standard table.
- Validate full ISO/DIN tolerance, fit, static/dynamic capacity and life calculations against documented reference cases. The current models and compact tables must be described as approximations until that work is completed.

## Release recommendation

Keep this PR as a draft until documented Blender/FreeCAD host tests and independent manufacturer/standard reference cases are completed. The CI matrix and ZIP parity check are green, but host-free tests do not establish manifoldness or BREP validity in a real CAD application and do not prove full ISO/DIN conformance.
