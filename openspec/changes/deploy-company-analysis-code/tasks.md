# Tasks

- [x] Confirm user's destination, exclusions and authorization.
- [x] Authenticate relay and identify actual company compute node.
- [x] Inspect GPU/driver, OS, free space and existing target directory.
- [x] Write source scope, deployment design and validation criteria.
- [x] Prepare and commit reusable deployment helpers before execution.
- [x] Build source bundle and exclusion/hash manifest.
- [ ] Transfer and verify complete source bundle, including OpenSpec.
- [ ] Report final source paths and integrity results, without claiming runtime readiness.

## Deferred by user's latest instruction

Do not install dependencies, download weights, or run models in this phase.
Python/GPU environment setup, package caches, forward/train/test checks and
company-dataset configuration remain future work.
