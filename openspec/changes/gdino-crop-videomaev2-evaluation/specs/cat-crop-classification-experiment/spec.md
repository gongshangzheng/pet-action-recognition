## Purpose

为猫行为分类实验提供可追溯的 GroundingDINO 空间裁剪视频，并在固定数据划分下训练与评估裁剪输入的 VideoMAEv2 分类器，完整暴露预处理失败和测试集复用的限制。

## ADDED Requirements

### Requirement: Traceable clean crop videos

The system SHALL preserve original videos and labels and write separate spatially cropped videos with source identity, source hash, detection and crop settings, output hash and frame mapping. Training videos MUST contain no rendered labels, state text, boxes or scores.

#### Scenario: Cropped video is eligible for training

- **WHEN** a crop video is admitted to a training or evaluation index
- **THEN** its decoded frame sequence and annotated frame bounds match the recorded source mapping
- **AND** the video contains only the cropped image content and has verified provenance

#### Scenario: Stale or incomplete output is encountered

- **WHEN** an output has incompatible source hashes, settings, dropped frames or an incomplete trajectory
- **THEN** the system rejects reuse and records the failure
- **AND** it does not silently pad with black frames or reuse the last trajectory record

### Requirement: Explicit target validity and pixel assistance

The system SHALL record detection, target species, interpolation and pixel-correction provenance separately. Pixel assistance MUST NOT classify a stationary pet as absent. Missing detections and unsupported multi-pet frames MUST remain visible, with no silent full-frame fallback that makes an invalid interval eligible for training or evaluation.

#### Scenario: An invalid frame is displayed for human review

- **WHEN** a frame is ineligible for training but is displayed in the review interface
- **THEN** the display uses the highest-confidence pet box, nearest same-species interpolation, or an edge-held box when the video has any pet anchor, while retaining its invalid status, reason, and long-gap marker
- **AND** the full source image appears only when the source video has no pet anchor at all
- **AND** display fallback does not admit the interval to the common training or evaluation index

#### Scenario: Camera rendering crosses an eligibility boundary

- **WHEN** a source video contains pet anchors and adjacent frames have different training eligibility
- **THEN** both frames use the same interpolated and edge-padded moving-average camera path
- **AND** missing detections do not switch rendering to the full source image
- **AND** oversized square windows use border padding without stretching or truncating the detected box
- **AND** pixel-assisted camera offsets use the legacy bounded damping with zero offset at detection anchors

#### Scenario: An index is built independently of rendering

- **WHEN** the system generates a training or evaluation index from existing crop artifacts
- **THEN** it checks the current source hash, detection fingerprint, render fingerprint, output paths and both media hashes before admission
- **AND** mismatched or missing assets remain unavailable with an explicit reason

#### Scenario: No reliable target exists

- **WHEN** an interval samples frames in a long detection gap or an unsupported multi-pet region
- **THEN** the interval is marked unavailable with the reason and split
- **AND** the report retains it in original-input coverage accounting

#### Scenario: Target species is the cat

- **WHEN** a frame contains exactly one cat, with or without dogs
- **THEN** the training target is that cat and the crop follows the cat box
- **AND** dogs in the same frame do not change the selected target
- **WHEN** a frame contains two or more cats
- **THEN** the interval is marked unavailable as `multi_pet_unsupported` because the target identity is ambiguous
- **WHEN** the training set is assembled
- **THEN** dog-only intervals are excluded and the exclusion is reported with counts by split
- **WHEN** a frame contains no reliable cat detection
- **THEN** the interval is marked unavailable as detection-missing
- **AND** the system does not interpret low pixel motion as proof that the pet is absent

#### Scenario: Pixel-assisted variant is generated but not trained

- **WHEN** the pixel-assisted variant is generated alongside the detection-only crop
- **THEN** both consume the same frozen detection cache and share detection anchors
- **AND** only the detection-only crop enters this training scope
- **AND** the assisted variant remains recorded for later analysis

### Requirement: Reproducible cropped-classifier training

The experiment SHALL train the classifier on the GroundingDINO crop arm (B) using a frozen index, one class mapping, a day-disjoint split, a documented pretrained initialization, a recorded training seed and a fixed recipe. Every run MUST record resolved configuration, hashes, environment, logs and completion status. Raw and pixel-assisted assets MAY exist, but only the crop arm is trained in this scope.

#### Scenario: Crop failures reduce the training set

- **WHEN** an interval has no eligible crop
- **THEN** it is excluded from the frozen index with a recorded reason
- **AND** the report states excluded counts by class and split and the resulting scope of the result

#### Scenario: Legacy assets are present

- **WHEN** a new experiment starts
- **THEN** it writes isolated output paths and preserves legacy rankings, metrics, checkpoints and source annotations

### Requirement: Frozen evaluation and honest metrics

The experiment SHALL select checkpoints and the preferred preprocessing variant using validation only, freeze that decision before testing, and report interval top-1 accuracy, macro-F1, balanced accuracy, per-class measures and sample counts. It MUST also report preprocessing availability and successful classification over the entire original evaluation index, counting unavailable inputs as unsuccessful.

#### Scenario: Testing follows selection

- **WHEN** all experiment arms have completed validation
- **THEN** a persisted selection record identifies their frozen checkpoints and preprocessing settings before their test runs
- **AND** test outcomes do not change that selection or trigger tuning on the same test set

#### Scenario: Accuracy is reported for the crop arm

- **WHEN** classification accuracy on the crop arm is reported
- **THEN** the report also provides the original denominator, crop failures and success rate over all original intervals
- **AND** it distinguishes conditional accuracy from pipeline availability
- **AND** it does not claim that cropping improved accuracy, because no raw-input arm is trained in this scope

#### Scenario: Previously used test data is reused

- **WHEN** the experiment evaluates the historical seven-class test split
- **THEN** the report labels the result as benchmark re-evaluation with prior test exposure
- **AND** it does not claim fresh independent validation, event-level miss rate or final product acceptance

### Requirement: Resource bounded preparation and evidence

Video preparation and model execution SHALL use bounded decoded-frame memory, resource checks and guarded remote execution. Each completed or failed run SHALL retain its status and evidence, and the experiment conclusion SHALL record negative results as well as improvements.

#### Scenario: Shared resources are occupied

- **WHEN** the resource check reports occupied GPU capacity or insufficient host resources
- **THEN** the experiment does not launch the workload and records the blocker

#### Scenario: An experiment shows no benefit

- **WHEN** cropped training fails to improve the frozen evaluation measures
- **THEN** the evidence records the observed result and limitations without claiming improvement or replacing the existing production model
