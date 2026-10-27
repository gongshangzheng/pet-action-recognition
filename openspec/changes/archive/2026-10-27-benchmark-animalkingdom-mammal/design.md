# Protocol

- Select one available best checkpoint per model by historical validation Top-1;
  never choose checkpoints using this test set. Record alternative candidates.
- Recover architecture and input normalization from saved training configs.
  Require seven output classes and strict state-dict loading.
- Single spatial center crop. One temporal clip for 3D recognizers; retain the
  required temporal segments for 2D models. Dense sampling uses one position.
  Retain architecture-specific resolution, frame count and interval; report them.
- Batch 1, FP32, TF32 off, seed 42, four CPU threads, one idle remote GPU.
- Accuracy: all 217 held-out clips, Top-1, macro/weighted F1, balanced accuracy,
  per-class precision/recall/F1/support, confusion matrices, raw scores, errors.
- Speed: 20 warmups and 100 repetitions on an actual preprocessed test input;
  report synchronized host and CUDA-event forward timing. The complete test pass
  separately measures decode/preprocess/transfer/predict/CPU-score latency.
- FLOPs: trace the same backbone + neck + classification-head forward, report
  unsupported operators and convention (one multiply-add is one operation).
- Each model runs in its own subprocess. Failures are recorded, not omitted.
- Preserve source/test/checkpoint hashes, resolved configs and software versions.
  Record imbalance, small-class uncertainty and original annotation limitations.

Implementation is committed locally and transferred verbatim into the isolated
remote results batch as a source snapshot, leaving the deployed repository's
tracked source and old experiment files untouched.
