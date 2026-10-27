# Install the company training and inference environment

The user explicitly authorized dependency installation after source deployment,
and explicitly prohibited running training or forward inference while the
company dataset is still being prepared. This request authorizes the install
phase; no additional review request is needed for the same scope.

Install an isolated, reproducible Python 3.10 environment under
`/home/work/analysis_code`. Audit the core MMAction2 train/inference/evaluation
entry points, preserve package downloads for unreliable networking, and record
installed versions and dependency-only validation results. Do not modify the
system Python, GPU driver, company data or unrelated environments.

Do not download model weights, build a model, run a forward/backward pass,
launch a training/test loop, access company samples, or start application
services. Successful imports and command-line help demonstrate environment
readiness, not an executed end-to-end model workflow.
