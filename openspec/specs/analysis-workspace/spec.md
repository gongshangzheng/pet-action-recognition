# analysis-workspace Specification

## Purpose

Define the scoped company source deployment, integrity evidence and readiness boundaries, while preserving unrelated environments and separating source transfer from runtime and model execution checks.

# Analysis workspace

Current phase covers source deployment and integrity only. Requirements for
runtime installation and GPU execution are explicitly deferred.

## Requirements

### Requirement: complete scoped source deployment
The target SHALL contain all dependencies of the project's core training,
inference and evaluation entry points, plus the full OpenSpec directory.

#### Scenario: source transfer
- WHEN the prepared archive is installed under /home/work/analysis_code
- THEN selected source hashes match the local manifest
- AND the original scheme image, project requirements and reading HTML are absent.

### Requirement: isolated and recoverable runtime
The deployment SHALL preserve the host driver and unrelated environments and
record a compatible dependency set with cached installation assets.

#### Scenario: Internet access ends
- WHEN the verified environment is used without fetching new packages or weights
- THEN the validated local forward/train/test workflow remains runnable
- AND missing optional weights or datasets are stated explicitly.

### Requirement: evidence for readiness
The completion report SHALL distinguish source-copy success, environment
installation, GPU forward/backward checks and company-dataset readiness.

#### Scenario: company data not yet configured
- WHEN only synthetic smoke inputs are available
- THEN report functional checks only and do not claim real-data training or accuracy.
