## Purpose

为猫行为分类实验提供可追溯的 GroundingDINO 空间裁剪视频与像素运动辅助变体，并在固定数据划分下比较 VideoMAEv2 分类结果，完整暴露预处理失败和测试集复用的限制。

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

The system SHALL record detection, interpolation and pixel-correction provenance separately. Pixel assistance MUST NOT classify a stationary pet as absent. Missing detections and ambiguous multi-cat targets MUST remain visible, with no silent full-frame fallback.

#### Scenario: No reliable target exists

- **WHEN** an interval samples frames in a long detection gap or an unresolved multi-cat region
- **THEN** the interval is marked unavailable with the reason and split
- **AND** the report retains it in original-input coverage accounting

#### Scenario: A dog is present or a cat is not detected

- **WHEN** sampled frames contain a dog or contain no reliable cat detection in a labeled cat-action interval
- **THEN** the interval is marked unavailable as target-ambiguous or detection-missing
- **AND** the system does not interpret low pixel motion as proof that the cat is absent

#### Scenario: Pixel correction is compared with detection-only cropping

- **WHEN** detection-only and pixel-assisted variants are generated
- **THEN** both consume the same frozen detection cache
- **AND** correction is distinguishable from detection and preserves sampled anchor boxes

### Requirement: Paired reproducible classifier training

The experiment SHALL compare raw input, detection-based cropping and cropping with pixel assistance using a frozen common sample set, identical class mapping, day-disjoint split, pretrained initialization, training seed and classifier recipe. Each run MUST record resolved configuration, hashes, environment, logs and completion status.

#### Scenario: Crop failures reduce the common sample set

- **WHEN** either crop variant cannot provide an eligible interval
- **THEN** all paired training arms use the same frozen common index
- **AND** the report states excluded counts by class and split and the resulting scope of comparison

#### Scenario: Legacy assets are present

- **WHEN** a new experiment starts
- **THEN** it writes isolated output paths and preserves legacy rankings, metrics, checkpoints and source annotations

### Requirement: Frozen evaluation and honest metrics

The experiment SHALL select checkpoints and the preferred preprocessing variant using validation only, freeze that decision before testing, and report interval top-1 accuracy, macro-F1, balanced accuracy, per-class measures and sample counts. It MUST also report preprocessing availability and successful classification over the entire original evaluation index, counting unavailable inputs as unsuccessful.

#### Scenario: Testing follows selection

- **WHEN** all experiment arms have completed validation
- **THEN** a persisted selection record identifies their frozen checkpoints and preprocessing settings before their test runs
- **AND** test outcomes do not change that selection or trigger tuning on the same test set

#### Scenario: Accuracy improves only on available crops

- **WHEN** successful-crop classification accuracy is reported
- **THEN** the report also provides the original denominator, crop failures and success rate over all original intervals
- **AND** it distinguishes conditional accuracy from pipeline availability

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
