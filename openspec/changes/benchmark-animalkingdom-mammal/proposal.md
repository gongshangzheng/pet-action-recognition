# AnimalKingdom mammal model comparison

User requested a complete model comparison and selected AnimalKingdom if it was
the prior fine-tuning source. Remote README, label mapping, and per-clip metadata
confirm that pet_action_mammal_v0 is an AnimalKingdom-derived seven-class strict
mammal subset (1801/216/217 train/validation/test). This is not the original
AnimalKingdom benchmark. Execute the requested evaluation without retraining.

Use existing validation-selected best fine-tuned checkpoints, stored training
configs, strict weight loading, full test coverage, per-class metrics and saved
predictions. Measure single-view inference and full video processing separately.
Write a new isolated results batch; preserve existing checkpoints and results.
