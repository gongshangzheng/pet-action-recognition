# Runtime readiness

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
