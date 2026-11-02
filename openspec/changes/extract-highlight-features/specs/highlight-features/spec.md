## ADDED Requirements

### Requirement: frame quality metrics

The extractor SHALL report per-window and whole-clip brightness (mean BT.601 luma / 255) and contrast (RMS luma std / 255, plus p5–p95 luma spread / 255) for every sampled frame, independent of pet detection.

#### Scenario: no pet in view

- **WHEN** no pet is detected in a clip
- **THEN** brightness and contrast are still reported and all pet-dependent durations are 0

### Requirement: pet body area ratio and duration

The extractor SHALL report the union pet area divided by frame area per sample, its summary statistics while the pet is visible, the pet-visible duration and segments, and the duration and segments in which the ratio is at least the configured large-body threshold. The payload SHALL state whether the area came from masks or boxes.

#### Scenario: box-only source

- **WHEN** the pet source provides boxes without masks
- **THEN** `analysis.area_source` is `box`

### Requirement: pet activity magnitude

The extractor SHALL report a motion energy computed inside the pet region between consecutive samples, minus the motion energy outside the region, clipped at 0, together with centroid displacement and a discrete activity level.

#### Scenario: global brightness change

- **WHEN** the whole frame brightens uniformly between two samples and the pet does not move
- **THEN** the reported activity for that step is approximately 0

### Requirement: face exposure ratio and duration

The extractor SHALL report face area divided by frame area, face-to-body area ratio, the face-exposed duration and segments, using a pluggable face source whose default needs no downloaded weights.

#### Scenario: face never detected

- **WHEN** no face is detected
- **THEN** face-exposed duration is 0 and the segment list is empty

### Requirement: behavior recognition information

The payload SHALL include a behavior timeline of merged segments with label, mean score and top-k when available, loaded from an existing timeline file or produced by a configured action model, and SHALL mark `abnormal` or low-confidence segments with `needs_cloud_review: true`.

#### Scenario: no behavior source

- **WHEN** no behavior source is configured
- **THEN** `behavior.source` is `none` and `behavior.segments` is an empty list

### Requirement: cloud report payload and local outbox

The extractor SHALL emit a `pet.highlight.v1` JSON payload with a deterministic `event_id`, device identifiers, source metadata, analysis settings, summary, segments, windows, behavior and a `cloud_judgement` field left `null`. The edge side SHALL NOT select or crop highlight clips; that decision belongs to the cloud. With an outbox directory configured it SHALL write the payload atomically and SHALL NOT overwrite an existing event file. No network upload is performed.

#### Scenario: repeated run

- **WHEN** the same video is processed twice with the same settings
- **THEN** both payloads have the same `event_id` and the second outbox write leaves the first file unchanged
