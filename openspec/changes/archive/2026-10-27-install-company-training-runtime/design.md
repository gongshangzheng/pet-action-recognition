# Design

Observed host: CentOS 7, glibc 2.17, Python 2.7.5, four NVIDIA A30 24 GB,
driver 525.85.12, approximately 310 GB free. Python 3/conda/ffmpeg are absent.
The authenticated interactive relay session is reusable. TUNA Miniconda HEAD
responds successfully. Large package downloads may require lengthy retries.

## Dependency selection

Use a glibc-2.17-compatible Miniconda Python 3.10 bootstrap in `.runtime/conda`,
and a venv at `.runtime/pet`. Start with the project's verified combination:
torch 2.1.2 (CUDA 12.1 Linux PyPI build), torchvision 0.16.2, mmcv 2.1.0
(prebuilt CUDA 12.1 / torch 2.1 wheel), mmengine 0.10.7, local mmaction2 1.2.0,
NumPy 1.26.4, and OpenCV 4.10.0.84. Keep package and bootstrap caches under
`.runtime/cache`; use resumable downloads where available. Download packages
from trusted HTTPS indexes/mirrors and retain the resolved wheel set.

Install video decoding/encoding and ordinary scientific dependencies required
by project imports, FastAPI for scripts importing the model registry, and
MMDetection 3.2.0 for registered AVA models. Inspect optional model integrations
before expanding scope; separate detection/tracking, pose and hardware-export
ecosystems are not implied by the core action-recognition environment.
The registered MViT training config requires PytorchVideoWrapper: install
PyTorchVideo 0.1.5 and verify its transforms import without applying transforms.
Retain MoviePy 1.0.3 for the AVA demo's moviepy.editor API and LMDB 1.5.1 for LFB.

Prefer binary wheels compatible with glibc 2.17. Pin older scientific/library
versions when current wheels require newer glibc. Do not replace system CUDA or
compile MMCV from source. Use one OpenCV provider when practical; reconcile the
upstream package metadata with pip check without silent incompatible upgrades.

## Validation boundary

Allowed: pip check, package/version/import checks, import MMCV compiled extension,
CUDA device discovery, FFmpeg version, parse model configs and custom imports,
verify train/test/inference CLI --help, inspect declared model class registration.
Do not instantiate a model/runner/dataloader, initialize weights, call any model
forward or backward, create synthetic model input, or read a real dataset.

Save logs, freeze/lock files, dependency cache inventory and a JSON validation
report under `results/deployment/company_runtime_20260930/`. Reusable install
and audit scripts must be committed locally before being run on the server.
Record the remaining data/label/checkpoint preparation and model execution checks
in the handoff rather than declaring the full training workflow tested.

The official Decord 0.6.0 py3 wheel contains a cp36-cp36m internal WHEEL tag.
Observed pip check reports only this platform-tag issue; Decord/native-library
import succeeds on the installed Python 3.10. Retain the raw diagnostic and
accept only this exact known warning after checking the metadata and import.
Do not suppress other dependency/version errors or claim decoding was tested.

Configuration audit found one pre-existing registry typo: LFB refers to
`8xb16`, while the vendored config and authoritative LFB metafile use `8xb12`.
Correct the project's config reference and corresponding pretrained URL to the
metafile values. Do not change vendored code or download the checkpoint.
