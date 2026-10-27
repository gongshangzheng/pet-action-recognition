## Purpose

Prepare reproducible offline installation and model assets with source provenance, verified payloads and resumable transfers, while distinguishing file availability from actual model execution readiness.

## ADDED Requirements

### Requirement: Record every prepared asset
Each asset SHALL record its purpose, upstream URL or pinned revision, local path,
size, SHA256, validation status and available upstream checksum.

#### Scenario: several model IDs share one checkpoint
- WHEN their upstream URLs are equal
- THEN download one payload and preserve all expected model-specific paths
- AND retain the pretrained metadata for each model ID.

### Requirement: Prepare files without running models
Preparation SHALL NOT construct models, deserialize pickle weights, train, infer,
quantize, use company datasets, or upgrade the working core environment.

#### Scenario: a model has only dataset-specific or private checkpoints
- WHEN no appropriate public asset is available
- THEN record that limitation rather than silently substitute a different trained model.

### Requirement: Resumable and verifiable downloads
Downloads SHALL retain partial files, verify transport length and available upstream
digests, reject error pages and LFS pointers, and avoid overwriting unrelated files.

#### Scenario: a URL is unavailable
- WHEN retries and verified upstream alternatives fail
- THEN preserve an actionable error and mark the asset missing
- AND do not report full readiness for that path.
