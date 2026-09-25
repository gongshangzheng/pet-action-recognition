- [x] Verify AnimalKingdom provenance and existing fine-tuning artifacts.
- [x] Implement reproducible evaluation and reporting.
- [x] Run all eligible fine-tuned RGB models on the remote GPU (18 models, 217 clips each).
- [x] Audit completeness, failures, metric calculations and report limitations (3906 predictions; independently checked with scikit-learn).
- [x] Copy reports and raw results locally and provide output paths.

Artifacts: `results/model_comparison/animalkingdom_mammal_20260925/` on both
local and remote project roots. Local ZIP is stored next to the batch directory.
All candidates completed after restoring the original TPN lazy classifier and
registering the original project LabelSmoothLoss. Both attempts are preserved.
Best measured checkpoint: VideoMAEv2-Base, Top-1 82.03%, Macro-F1 63.01%.
