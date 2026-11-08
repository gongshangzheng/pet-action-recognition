## ADDED Requirements

### Requirement: Distinguish installation from execution readiness
The report SHALL distinguish dependency import checks, real model computation,
controller contract checks, end-to-end coverage, and semantic quality evaluation.

#### Scenario: a random detector emits no boxes
- WHEN its forward and postprocessing succeed on synthetic video
- THEN the candidate computation check may pass
- AND cat-detection quality SHALL remain unverified
- AND unvisited downstream branches SHALL be reported explicitly.

### Requirement: Separate module and composition checks
Each selected module SHALL have an independent check, followed by same-process
execution and data-handoff checks using explicit shape, color, coordinate and time contracts.

#### Scenario: controlled presence scores activate a downstream branch
- WHEN the harness injects scores to exercise clip closure and mask processing
- THEN the report SHALL identify the injected data and actually executed models
- AND SHALL NOT label this as successful semantic cat detection.

### Requirement: Verify a bounded training lifecycle
Selected trainable paths SHALL verify finite loss and gradients, parameter updates,
checkpoint round-trip and an action-model optimizer/scheduler resume and evaluation path.

#### Scenario: only the underlying MMAction2 Runner is exercised
- WHEN the project wrapper has not been executed
- THEN its coverage SHALL remain not_run
- AND the report SHALL NOT claim the complete project wrapper workflow passed.

### Requirement: Verify temporal accounting and buffer limits
Online/buffered checks SHALL declare lookahead, exit persistence, post-roll and queue limits,
and SHALL separate media clip-end error from wall-clock decision latency.

#### Scenario: input arrives faster than processing
- WHEN a controlled processing delay is injected
- THEN bounded queues and an explicit drop/backpressure policy SHALL be checked
- AND dropped frames, source timestamps and EOF handling SHALL be reported.

### Requirement: State model-export and hardware limitations
ONNX and RKNN SHALL be tested on explicitly named networks and target platforms.
Successful import or export alone SHALL NOT be reported as successful simulator inference.

#### Scenario: RV1126B simulation cannot initialize
- WHEN target initialization or inference fails
- THEN retain the error and report the failed or unsupported phase
- AND do not substitute another target or claim board latency measurements.

### Requirement: Preserve project data and execution scope
After approval, tests SHALL execute only on the company server in the existing environment,
using synthetic fixtures and isolated project result paths. No company datasets or external
weights SHALL be accessed by default. Reusable scripts SHALL be committed before execution.

#### Scenario: rembg weights are absent
- WHEN no compatible U2-NetP ONNX file is available under the approved scope
- THEN record pending_weights without automatic downloading
- AND do not use another segmentation model's passing result to satisfy the rembg check.
