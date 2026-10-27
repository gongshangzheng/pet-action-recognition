# Tasks

- [x] Confirm user's destination, exclusions and authorization.
- [x] Authenticate relay and identify actual company compute node.
- [x] Inspect GPU/driver, OS, free space and existing target directory.
- [x] Write source scope, deployment design and validation criteria.
- [x] Prepare and commit reusable deployment helpers before execution.
- [x] Build source bundle and exclusion/hash manifest.
- [x] Transfer and verify complete source bundle, including OpenSpec.
- [x] Report final source paths and integrity results, without claiming runtime readiness.

Source-only deployment completed on 2026-09-30 at
`work@10.33.37.211:/home/work/analysis_code`: 1,358 source files, including 165
OpenSpec files. All source hashes passed verification; no HTML was deployed.
Server evidence: `.deployment/verification.json`. Local evidence:
`results/deployment/company_analysis_code_20260930_final/`.
The transfer helper was corrected to decode UTF-8 archive names on Python 2.7;
no dependency installation was needed for source transfer and verification.

## Deferred by user's latest instruction

Do not install dependencies, download weights, or run models in this phase.
Python/GPU environment setup, package caches, forward/train/test checks and
company-dataset configuration remain future work.
