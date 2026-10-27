# model-comparison Specification

## Purpose

Provide a reproducible comparison on the AnimalKingdom-derived mammal subset while preserving sample-level evidence, strict checkpoint compatibility and the boundary between measured evaluation and historical training metadata.

## Requirements

### Requirement: Identify the evaluation population
The report SHALL identify the dataset as the AnimalKingdom-derived mammal subset and retain the unchanged test manifest, every sample prediction, failures and explicit model exclusions.

#### Scenario: A candidate cannot complete evaluation
- WHEN a candidate or sample fails
- THEN preserve the failure and exclusion reason without silently changing the test population.

### Requirement: Load checkpoints strictly and preserve existing assets
Classifier-head mismatches SHALL fail rather than silently initialize a new classifier. Evaluation SHALL NOT retrain, change datasets, replace checkpoints or overwrite old results.

#### Scenario: Classifier shape is incompatible
- WHEN checkpoint head dimensions do not match the intended model
- THEN stop that attempt and preserve its error without accepting randomly initialized head predictions.

### Requirement: Retain reproducible local results
Local artifacts SHALL include a readable report, machine-readable comparison, per-class results and reproducible commands. Reports SHALL separate measured evaluation and timing from historical training metadata and identify the timing scope.

#### Scenario: Results are handed off
- WHEN the comparison is complete
- THEN the local report links raw predictions and failures, records commands and separates measured results from historical training information.
