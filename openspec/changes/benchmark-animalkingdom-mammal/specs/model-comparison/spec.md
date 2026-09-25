# Model comparison requirements

The report must identify the dataset as AnimalKingdom-derived mammal subset,
provide the unchanged test manifest, preserve every sample prediction and failure,
include explicit model exclusions, and separate measured results from historical
training metadata. Head mismatches must fail rather than silently initialize a
new classifier. No retraining, dataset changes, checkpoint replacement or old
result overwriting is permitted. Local artifacts must include a readable report,
machine-readable comparison, per-class results and reproducible commands.
