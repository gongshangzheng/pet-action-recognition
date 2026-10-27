# Tasks

- [x] Re-read the three-direction research and confirm shared-environment preference.
- [x] Inspect candidate metadata and host/core-version compatibility.
- [x] Commit dependency pins and shared-environment installation/audit helpers.
- [x] Transfer helpers and plan, snapshot existing versions and native libraries.
- [x] Resolve with constraints and reject unplanned version changes.
- [x] Cache and install compatible auxiliary dependencies.
- [x] Verify auxiliary imports and unchanged core behavior at the dependency level.
- [x] Record RKNN support/limitations, version delta and handoff paths.

Completed 2026-09-30: 48 added packages in the original `.runtime/pet`;
only existing-version change is protobuf 7.36.2 -> 4.25.4. All 27 auxiliary
checks and 69 original-runtime checks passed. The original Decord internal
wheel-tag warning remains documented; no new unresolved dependency conflict.
Four native-module hashes are unchanged. RKNN import and shipped RV1126B
reference were checked; no conversion or simulator execution was performed.

Evidence: `results/deployment/company_auxiliary_20260930/auxiliary_audit.json`
and `core_recheck/runtime_audit.json`; handoff: `docs/company_auxiliary_runtime.md`.

Not authorized: model construction, training/forward/evaluation, dataset access,
weight downloads, quantization, simulator inference or board benchmarks.
