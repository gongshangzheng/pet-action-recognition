# Prepare dependencies for the three auxiliary research directions

The user requested likely dependencies for the previously researched background
removal, action-boundary segmentation and cat-presence models, and explicitly
prefers installing compatible packages into the existing `.runtime/pet`.
This authorizes the dependency installation. Keep the existing prohibition on
model execution, dataset processing and weight downloads.

Use the saved 2026-09-26 research report as the candidate list: U2-NetP/rembg,
torchvision LR-ASPP, YOLO11/seg and original YOLOv5/NanoDet alternatives,
MobileNetV3/ShuffleNetV2, change-point/HMM tools and small temporal networks.
Prepare ONNX export and RKNN-Toolkit2 2.3.2 for the confirmed RV1126B platform.

Do not replace the working action-recognition stack. Resolve and inspect the
installation before applying it, cache wheels, and recheck the old environment.
Explain that installed but unused libraries mainly consume disk; changed
backends, numerical libraries, preprocessing, quantization and concurrent model
execution can affect speed, numerical outputs or accuracy.
