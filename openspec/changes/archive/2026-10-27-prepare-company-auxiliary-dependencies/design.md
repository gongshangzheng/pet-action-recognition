# Design

## Existing environment and selected coverage

The company host uses CentOS 7/glibc 2.17 and Python 3.10.10. Keep the existing
torch 2.1.2, torchvision 0.16.2, CUDA packages, mmcv 2.1.0, mmengine 0.10.7,
mmaction2 1.2.0 and NumPy 1.26.4. Torchvision already supplies LR-ASPP,
MobileNetV3 and ShuffleNetV2; the small TCN examples can use ordinary torch.

Add rembg 2.0.59 (Python 3.10 compatible), CPU ONNX Runtime 1.16.3, pinned
Numba/PyMatting for masks; Ultralytics 8.3.0 (YOLO11 support), augmentation,
training and assignment utilities useful for the detector alternatives;
ruptures, hmmlearn and pytorch-tcn for sequence/boundary experiments;
onnx/onnxsim/onnxoptimizer and rknn-toolkit2 2.3.2 for export and board preparation.
Do not install unrelated large TensorFlow, VLM, SAM2 or pose ecosystems.
Model source implementations, pretrained weights and runnable board benchmarks
are separate from installing these reusable dependencies.

## Compatibility evidence and safeguards

PyPI metadata confirms rknn-toolkit2 2.3.2 has a cp310/manylinux_2_17 x86_64
wheel and requires torch >=1.10.1,<=2.4.0 and numpy <=1.26.4. It requires
protobuf >=4.21.6,<=4.25.4, so protobuf 4.25.4 is the only pre-authorized version
change among existing packages, subject to successful dependency resolution
and imports. ONNX Runtime GPU 1.17.1 requires manylinux_2_28; do not force it
onto this glibc-2.17 host. CPU ORT is a preparation/functional backend, not a
claim of accelerated rembg inference or RV1126B speed simulation. Existing
PyTorch CUDA support must remain unchanged.

Freeze all other existing installed distributions as constraints. Record a
before snapshot, run pip dry-run/report, and reject unplanned upgrades or
downgrades before installation. Preserve the existing OpenCV cv2 binary and
MMCV/Torch extension hashes. Some packages declare opencv-python-headless,
which shares the cv2 namespace with existing OpenCV distributions: pin exactly
4.10.0.84 and restore the cached original provider wheel after installation;
verify the native binary and build information remain the same.

Cache downloaded wheels under `.runtime/cache/auxiliary-wheels`. Keep any source
wheel builds confined to installation assets. Import-only validation must not
construct models, rembg sessions, ONNX sessions, RKNN objects or pipelines.
Do not download weights or touch datasets. Inspect RKNN import and its shipped
platform definitions for RV1126B; no build, quantization, simulator run or board
performance test is authorized. If native import fails despite compatible
metadata, record the actual cause and avoid declaring that component ready.

## Performance and reproducibility

Adding unused packages does not change model weights or inherently consume GPU
memory. Library version replacement, runtime/provider choice, precision,
quantization and preprocessing can change results and speed. Optional libraries
can enable framework-specific behavior (for example YOLO augmentation), so pin
experiment configs/seeds and record the actual pipeline. Never infer board
latency from host ORT or RKNN software simulation.

Store receipts, version deltas, install plan, package hashes and import audits in
`results/deployment/company_auxiliary_20260930/`; add a Markdown handoff. Keep
the prior HTML report local. Commit reusable helpers before running them.
