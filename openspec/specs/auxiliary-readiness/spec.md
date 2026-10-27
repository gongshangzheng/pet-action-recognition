# auxiliary-readiness Specification

## Purpose

This capability defines auditable acceptance criteria and evidence boundaries for the approved work, preserving reproducibility and distinguishing verified outcomes from remaining limitations.

## Requirements

### Requirement: reuse the working environment safely
Compatible auxiliary dependencies SHALL be installed in `.runtime/pet` with
the action-recognition core versions and native libraries preserved.

#### Scenario: dependency resolver requests a change
- WHEN the proposed install changes an existing distribution
- THEN reject it unless it is the documented protobuf compatibility adjustment
- AND verify dependency consistency and core imports after the installation.

### Requirement: bounded validation
Validation SHALL use imports, version inspection, metadata and existing CLI
help/config checks without model or dataset execution.

#### Scenario: board tools are installed on the server
- WHEN RKNN-Toolkit2 imports successfully and lists RV1126B
- THEN report toolkit availability only
- AND do not claim actual conversion, simulator accuracy or board speed tested.

### Requirement: explain performance effects accurately
The handoff SHALL distinguish the disk cost of unused packages from changes to
numeric backends, active pipelines, quantization or resource contention.

#### Scenario: Explain unused dependency costs
- WHEN the handoff describes an installed but unused package
- THEN distinguish its disk cost from effects of active numeric backends, quantization and resource contention without asserting an unmeasured speed change.
