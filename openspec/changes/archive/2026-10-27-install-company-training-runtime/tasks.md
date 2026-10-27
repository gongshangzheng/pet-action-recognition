# Tasks

- [x] Confirm install authorization and prohibition on model execution.
- [x] Audit core imports, existing host, driver and glibc compatibility.
- [x] Commit installation, dependency constraints and audit helpers.
- [x] Transfer helpers and this OpenSpec change to the company workspace.
- [x] Install isolated Python and download/cache the compatible dependency set.
- [x] Install core runtime, local MMAction2 and registered AVA dependencies.
- [x] Check dependency consistency, imports, CUDA visibility and CLI/config loading.
- [x] Record version locks, logs, cache inventory and handoff instructions.

Completed 2026-09-30: `.runtime/pet/bin/python` is Python 3.10.10. The final
audit contains 69 checks with no unresolved failure, 32 config-file parse
checks (including the config package initializer), and four visible A30 GPUs.
Status is `passed_with_packaging_warning`: only the explicitly diagnosed
Decord internal cp36 wheel-tag mismatch remains; its native import passed.
The local and remote LFB registry references were corrected to the vendored
8xb12 config and corresponding authoritative checkpoint URL.

Approximately 3.0 GiB of wheels are retained in `.runtime/cache/wheels`.
Evidence: `results/deployment/company_runtime_20260930/runtime_audit.json`,
`pip-freeze.txt`, `packages.json`, `wheels.sha256`, installation and audit logs.
Usage and offline restore instructions: `docs/company_runtime.md`.
No model was constructed or executed; no weights or dataset were processed.

Deferred: datasets/labels/checkpoints, actual training, evaluation and inference.
