# Deploy training and evaluation workspace to company GPU server

## Current phase: code transfer only

The user's latest instruction explicitly narrows this phase to copying local
code and OpenSpec. Do not install dependencies, download weights, or run model
training/inference in this phase. Runtime setup and GPU checks below describe
future work and are deferred. Completion for this phase means source integrity,
not a claim that the unconfigured server can already train.

## Request and scope

The user explicitly requested transferring all training, forward-inference and
evaluation dependencies from pet-final to `/home/work/analysis_code`, including
OpenSpec, and making the resulting server workspace runnable before its temporary
Internet access expires. The user subsequently confirmed the destination as
`work@10.33.37.211` through the company interactive relay and authorized login.

Include the complete local MMAction2 snapshot, project Python modules, custom
models/hooks/configurations, CLI entry points and OpenSpec history. Exclude the
original scheme image, project-requirements text, reading/report HTML, Windows
environments, personal SSH configuration and unrelated runtime databases.

## Observed environment

- Host: gpu0006.kj01.zzjg.dxm-int.com; account work.
- CentOS 7 x86_64; four NVIDIA A30 24GB; driver 525.85.12.
- Approximately 310GB available on /home; target directory absent initially.
- System Python 3 / conda absent. No local checkpoints/ or datasets/ to copy.

## Deliverable

A checksummed source bundle, isolated Python environment, cached installation
assets, dependency/version records, offline operation instructions, and evidence
from short GPU forward/training/evaluation checks. Company-dataset training is
configured only once its actual paths and labels are known; no long training run
is implied by environment validation.

## Authorization boundary

Proceed within the user's explicit transfer-and-runnability request. Preserve
unrelated remote files and existing processes. Do not persist authentication
secrets. Keep company data on the company server. Do not claim all models or an
unavailable dataset were validated when only a bounded smoke check was run.
