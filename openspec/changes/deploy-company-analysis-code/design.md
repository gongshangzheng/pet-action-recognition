# Design

The current execution scope is source packaging, transfer and SHA256 validation
only. Environment installation and model execution are deferred by the user's
latest instruction. Use only already-present system utilities for the transfer.

## Source completeness

Package scripts/, configs/, server/, petlib/, evaluation/, models/, openspec/,
deployment documentation and root metadata. Preserve MMAction2 config inheritance,
requirements, tools, projects and label maps. Transfer a manifest of relative
paths, byte counts and SHA256 hashes. Reading HTML and the user's two root input
documents are excluded. The transfer artifact is generated under results/.
Upstream demo media, documentation images and library unit-test data fixtures are
excluded from this code-only transfer; their Python source is retained. These are
not the company's training data or the project's model evaluation entry points.

No local checkpoint or dataset directory exists. Document this and prepare
public weight downloads explicitly; copying code is not a substitute for weights
or labeled company data. Do not substitute old AnimalKingdom paths for company
data. Legacy batch scripts with fixed home/Python paths need portable invocation
or a documented replacement entry point.

## Runtime

Use an isolated prefix under the requested workspace. Start with Python 3.10,
PyTorch 2.1.2/cu121, torchvision 0.16.2, mmcv 2.1.0, mmengine 0.10.7,
MMAction2 1.2.0, NumPy 1.26.4 and OpenCV 4.10.0.84. Verify actual wheel and glibc
compatibility on CentOS 7 before installing. Preserve the installed host driver;
do not require a system CUDA reinstall for prebuilt PyTorch/MMCV wheels.

Cache bootstrap installers, conda packages where used, pip wheels and version
locks under analysis_code. Install local MMAction2 without silently resolving
new incompatible core versions. Additional detector/RKNN ecosystems may require
separate environments; do not destabilize the action-recognition environment to
install every optional project from upstream examples.

## Transfer and validation

The company relay is an authenticated interactive gateway, not a normal shell.
Prefer an allowed transfer mechanism; if reusing the authenticated terminal,
frame binary data safely, verify size/hash, and extract only relative members
within the intended workspace. Never disable SSH host identity checking.

Verify imports and compiled MMCV operations, decode a small test video, perform
GPU inference, a bounded optimizer update, checkpoint save/reload and evaluation.
When possible exercise the actual train/test CLI with a generated miniature
fixture. Label synthetic data checks as functional checks, not model accuracy.
Record logs and unresolved optional dependencies. Check offline readiness of the
validated path rather than merely reporting a successful pip install.
