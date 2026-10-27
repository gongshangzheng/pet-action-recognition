# cat-action-training Specification

## Purpose

Establish the reproducible seven-class cat interval training protocol with deterministic day-disjoint splits, preserved source labels, validation-only model selection and explicit clip-level evaluation boundaries.

## Requirements

### Requirement: versioned derived labels with provenance

The system SHALL generate a versioned derived label set without modifying the
original videos or annotations. All abnormal source labels SHALL map to one
`abnormal` class; `common/toileting` SHALL map to a distinct `toileting` class.
The mapping, source SHA-256, output SHA-256 and dropped-record counts SHALL be
recorded.

#### Scenario: abnormal labels are merged

- **WHEN** a source interval has label `abnormal/scratching`, `abnormal/gnawing`,
  `abnormal/fall` or `abnormal/seizure`
- **THEN** its v1 label is `abnormal`
- **AND** the original label is preserved in the mapping audit

#### Scenario: toileting is a distinct class

- **WHEN** a source interval has label `common/toileting`
- **THEN** its v1 label is `toileting`
- **AND** it is not merged into `abnormal` or `activity`

#### Scenario: original annotations remain unchanged

- **WHEN** the derived label set has been generated
- **THEN** `datasets/cat_raw/annotations/intervals.csv` has the same byte content
  and SHA-256 as before the run
- **AND** no original video is copied, re-encoded or overwritten

### Requirement: deterministic interval filtering and day-disjoint split

The system SHALL filter intervals using the existing v1 protocol: 1-based
inclusive frame ranges, at least 60 frames, and no overlap with any other
interval in the same video. The train/val/test split SHALL be disjoint by event
calendar day, use a recorded seed, and SHALL provide enough samples in every
class for the validation and test views. The v1 protocol SHALL require at least
four `toileting` samples in validation and at least four in test.

#### Scenario: an overlapping interval is excluded

- **WHEN** an interval overlaps any other interval in the same video
- **THEN** it is not included in the v1 training index
- **AND** the exclusion reason and source label are counted in the audit

#### Scenario: split is reproducible

- **WHEN** the index generator is run again with the same source and seed
- **THEN** it produces byte-identical JSONL and manifest files
- **AND** no event calendar day appears in more than one split

### Requirement: use all training candidates and distinct evaluation views

The training split SHALL include every eligible candidate assigned to training
days, rather than a fixed per-class quota. Validation and test SHALL each expose
a natural-distribution view and a balanced diagnostic view; the natural view
SHALL be used for model selection and the balanced view for per-class diagnosis.

#### Scenario: class imbalance is handled during training

- **WHEN** the training index is larger for `activity` than for `grooming` or
  `drinking`
- **THEN** the training configuration records a class-balancing method
  (weighted loss or sampler)
- **AND** the validation/test natural distributions are not artificially
  balanced

#### Scenario: balanced diagnostic view is reproducible

- **WHEN** a balanced diagnostic view is requested
- **THEN** at most 12 samples per class are selected from each split by a fixed,
  recorded rule
- **AND** the selected sample IDs and their hashes are recorded

### Requirement: backup and run reproducibility

Before replacing or regenerating any tracked working files, the system SHALL
create and verify a backup of the local Git state and the remote worktree state
that could be overwritten. All code and configuration changes SHALL be committed
locally before synchronization; the remote SHALL NOT be edited by hand. Every
run SHALL record its config, dataset hashes, environment versions, logs,
checkpoint hashes and output path.

#### Scenario: remote worktree is backed up before synchronization

- **WHEN** the remote worktree has modified or untracked files
- **THEN** its tracked changes and relevant untracked files are archived with a
  manifest before any sync or clean operation
- **AND** the backup path is recorded in the run report

#### Scenario: run evidence is auditable

- **WHEN** a training or test run completes
- **THEN** the output directory contains a run status, config and index hashes,
  terminal logs, metrics and checkpoint path
- **AND** the report identifies the environment versions used

### Requirement: select the first training model on validation only

The system SHALL train TSN R50 and TSM R50 under the same v1 index, sampling and
augmentation protocol. Model selection SHALL use validation macro-F1 as the
primary criterion and per-class recall, especially `toileting`, `abnormal`,
`grooming` and `drinking`, as secondary criteria. The test set SHALL NOT be used
to select or tune the model.

#### Scenario: one model is selected

- **WHEN** both candidates have completed validation
- **THEN** the selection record names the winner and reports both candidates'
  validation macro-F1 and per-class recall
- **AND** the test metrics are produced only after selection

#### Scenario: test set is evaluated once per candidate

- **WHEN** the model has been selected
- **THEN** both candidates' test results may be reported for transparency
- **AND** the selection rationale does not depend on the test results

### Requirement: report merged abnormal-class recall

The evaluation output SHALL report recall and support for the merged `abnormal`
class as one class in both validation and test. The run summary and model
selection record SHALL surface `abnormal` recall and support explicitly. The
system SHALL NOT claim recall for the four source anomaly subtypes separately.

#### Scenario: abnormal recall is reported

- **WHEN** validation or test metrics are produced
- **THEN** the per-class report includes `abnormal` support, precision, recall and F1
- **AND** the run summary and selection record include the merged `abnormal`
  recall and support

#### Scenario: subtype recall is not claimed

- **WHEN** abnormal metrics are reported
- **THEN** they describe the merged `abnormal` class only
- **AND** no separate scratching/gnawing/fall/seizure recall is claimed

### Requirement: v1 training boundary

The v1 label set SHALL contain exactly the seven classes `activity`, `eating`,
`drinking`, `prolonged_stationary`, `grooming`, `toileting`, `abnormal`.
Multi-cat interactions, audio-based meowing and independent rare-anomaly classes
SHALL be explicitly out of scope for this change. Multi-cat chase/roughplay
SHALL be deferred to a future spatial-relation rule, not an action classifier.

#### Scenario: excluded source labels are visible

- **WHEN** source intervals carry `common/multi_cat_chase` or
  `common/multi_cat_roughplay` labels
- **THEN** they are excluded from v1 and their counts are reported in the audit
- **AND** they are not silently mapped into a v1 class

#### Scenario: multi-cat is not delegated to the action model

- **WHEN** the v1 report describes multi-cat chase or roughplay
- **THEN** it records the future spatial-relation approach
- **AND** it does not claim a trained v1 classifier for those behaviors

#### Scenario: timeline evaluation is not claimed

- **WHEN** v1 metrics are reported
- **THEN** they are labeled as clip-level interval metrics
- **AND** no event-level miss rate or continuous-timeline acceptance result is
  claimed
