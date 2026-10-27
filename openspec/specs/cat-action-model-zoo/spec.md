# cat-action-model-zoo Specification

## Purpose

This capability defines auditable acceptance criteria and evidence boundaries for the approved work, preserving reproducibility and distinguishing verified outcomes from remaining limitations.

## Requirements

### Requirement: same-protocol reference models

Additional models SHALL be trained on the unchanged v1 seven-class index and split, with results written to per-model directories that do not overwrite the TSM/TSN results.

#### Scenario: v1 assets are unchanged

- **WHEN** the batch finishes
- **THEN** the v1 index hashes and the TSM/TSN `run_status.json` files are unchanged

### Requirement: pretrained weights verifiably loaded

Each model SHALL pass a preflight showing that backbone tensors equal the checkpoint tensors, that sampled frames lie inside the labeled interval, and that a real batch fits in GPU memory.

#### Scenario: preflight fails

- **WHEN** weights do not load or frames fall outside the interval
- **THEN** that model is not trained until its configuration is fixed

### Requirement: validation-only ranking, frozen before testing

Ranking SHALL use validation macro-F1 first, then toileting, abnormal, grooming and drinking recall. The ranking file SHALL be written before any new model's test split is evaluated.

#### Scenario: test follows ranking

- **WHEN** the test stage starts
- **THEN** `model_zoo_ranking.json` already exists and test metrics are not used to change it

### Requirement: disclose non-controlled differences

The report SHALL list differences from the TSM/TSN baselines (precision, weight loading route, cropping, temporal span, regularization) and SHALL NOT present small macro-F1 gaps as established differences given the small validation support.

#### Scenario: Interpret small score differences
- WHEN the reference models are compared with TSM and TSN
- THEN list precision, loading, crop, temporal and regularization differences and do not describe small validation gaps as established superiority.
