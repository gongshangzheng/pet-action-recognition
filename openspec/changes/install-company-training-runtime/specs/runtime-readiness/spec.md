# Runtime readiness

## Purpose

This capability defines auditable acceptance criteria and evidence boundaries for the approved work, preserving reproducibility and distinguishing verified outcomes from remaining limitations.

## ADDED Requirements

### Requirement: isolated compatible installation
The workspace SHALL provide a Python 3.10 environment with mutually compatible
PyTorch, MMCV, MMEngine, local MMAction2 and required data-processing dependencies.
It SHALL preserve the system Python, GPU driver and unrelated files.

#### Scenario: imports and command entry points
- WHEN dependencies have been installed
- THEN dependency consistency, required imports, extension loading and CLI help pass
- AND CUDA devices are discoverable without executing any model computation.

### Requirement: honor the no-execution boundary
The installation SHALL NOT run training, forward inference, evaluation loops,
weight initialization or dataset processing.

#### Scenario: incomplete company dataset
- WHEN dependency-only checks pass
- THEN report the exact checks and remaining data/checkpoint requirements
- AND do not claim that a training or forward pass was executed successfully.

### Requirement: recoverable downloads
The workspace SHALL retain downloaded installation assets and exact resolved
versions, with logs under the project tree, for later recovery after public
network access expires.

#### Scenario: Recover cached installation assets
- WHEN the environment must be restored after public access expires
- THEN retain resolved versions, installation assets and project-local logs so recovery inputs can be identified.
