# 三个附加方向的备用依赖

沿用服务器现有环境：`/home/work/analysis_code/.runtime/pet`。
本次只安装和检查依赖，不构建模型、不下载权重、不训练、不做前向、量化或模拟器推理。

2026-09-30 已完成补装，全部进入原有 `.runtime/pet`，没有新建第二套环境。
新增 48 个包（含间接依赖），原有包只将 `protobuf` 从 7.36.2 调整到 4.25.4。
27 项附加检查通过，原动作识别环境的 69 项检查也通过，未发现新增依赖冲突。
原有 Decord 0.6.0 的 wheel 标签警告仍存在，原生库导入正常；该问题及检查边界
见 [原环境说明](company_runtime.md)。

Torch 2.1.2 / CUDA 12.1、torchvision 0.16.2、MMCV 2.1.0、MMEngine 0.10.7、
MMAction2 1.2.0、NumPy 1.26.4 等保持原版本。Torch、MMCV、NumPy、OpenCV
四项关键原生库的 SHA256 与安装前一致。RKNN API 导入成功，已安装包中能找到
`rv1126b` 平台引用，但尚未验证任何模型的转换、模拟器运行或板端速度。

## 依赖与研究方案的对应关系

| 方向 | 已有或新增的库 | 用途与边界 |
|---|---|---|
| 背景移除 | torchvision、rembg、PyMatting、Numba、OpenCV | LR-ASPP 的模型实现已有；rembg 支持 U2-NetP 等 ONNX 掩码基线。训练 U2-Net 原始模型仍需对应源码与训练配置。 |
| 猫存在性 | torchvision、Ultralytics、timm、Albumentations、Lightning、TorchMetrics、lap | MobileNetV3/ShuffleNetV2、YOLO11/seg 及轻量检测研究通用依赖。原版 YOLOv5n、NanoDet 仍需锁定其源码版本和配置；不能把 YOLOv5nu 当成原版 YOLOv5n。 |
| 动作边界 | NumPy/SciPy、ruptures、hmmlearn、pytorch-tcn、h5py | 变化点/PELT、HMM、TCN 与特征存储。MS-TCN/ASFormer/ASRF 的具体模型源码、标注或外部特征仍需另外准备。 |
| 导出与板端准备 | ONNX、ONNX Simplifier、ONNX Optimizer、ONNX Runtime、RKNN-Toolkit2 2.3.2 | 为 RV1126B 转换与量化实验准备工具；安装不等于已经转换成功或测得板端速度。 |

服务器是 CentOS 7 / glibc 2.17，因此备用 ONNX Runtime 采用 CPU 1.16.3。
较新的 ONNX Runtime GPU wheel 要求更高 glibc，未强行安装；这不影响现有
PyTorch CUDA 环境，Torch/torchvision 模型仍可在准备好后使用 A30。
rembg 使用这一 ORT 后端时运行在 CPU，不能将它的耗时当成 GPU 或板端性能。

## 对现有模型性能有什么影响

只安装而不调用的库主要占磁盘，通常不会占用 GPU 显存或改变模型精度。
安装流程锁住原有依赖版本，仅允许 RKNN 要求的 protobuf 4.25.4 调整，
并比对 Torch、MMCV、NumPy 和 OpenCV 的关键原生库哈希。
protobuf 用于序列化，版本调整本身不会修改模型权重或浮点计算实现。

真正可能影响结果的是：改变预处理/数据增强、输入大小、阈值、执行后端、
精度或 INT8 量化；多个模型同时运行则会争用 CPU/GPU 和内存，增加延迟。
另需注意，有些框架会根据可选库是否安装选择行为，例如 YOLO 可启用
Albumentations 增强。新实验应明确记录实际增强管线、参数、版本和种子，
不能将“核心库没有升级”理解为所有新实验配置都天然一致。
本次没有跑速度或精度实验，不提供“性能提升/下降多少”的结论。

## 使用与记录位置

```bash
cd /home/work/analysis_code
source .runtime/pet/bin/activate
export YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR=/home/work/analysis_code/.runtime/cache/ultralytics
export U2NET_HOME=/home/work/analysis_code/.runtime/cache/rembg-models
export NUMBA_CACHE_DIR=/home/work/analysis_code/.runtime/cache/numba
```

- 固定依赖：`configs/company_auxiliary_requirements.txt`。
- 可复用安装/检查工具：`scripts/install_company_auxiliary.py`。
- 缓存：`.runtime/cache/auxiliary-wheels/`，原有缓存仍在 `.runtime/cache/wheels/`。
- 安装计划、前后版本、二进制哈希和审计：`results/deployment/company_auxiliary_20260930/`。
- 原有动作识别环境复查：该目录下的 `core_recheck/runtime_audit.json`。

本地也保留了核心审计、安装前后版本、freeze 和 wheel 哈希的副本：
`E:\pet-final\results\deployment\company_auxiliary_20260930\`。
完整安装日志、每个库的导入日志和解析器安装报告保留在服务器对应目录。

`auxiliary_audit.json` 是最终状态依据。日志中的导入成功只说明依赖可加载，
不等于已验证数据集、模型权重、完整训练或 RV1126B 的模拟/实机性能。

依赖复查可以单独执行，不触发模型运行或重新安装：

```bash
python scripts/install_company_auxiliary.py --root /home/work/analysis_code --audit-only
```

OpenCV 的 core/contrib/headless 包会共用 `cv2` 路径。这里固定相同版本，
并在补装后恢复安装前的原始 provider wheel，校验其原生库哈希。
后续升级或卸载其中一个包时需要一并检查 `cv2`，不能只看 pip 包名。
原始 provider 的缓存路径记录在本次审计目录的 `before.json` 中。

网络关闭后，原动作识别环境仍在的情况下，可从缓存补装这批依赖：

```bash
python -m pip install --no-index \
  --find-links .runtime/cache/auxiliary-wheels --find-links .runtime/cache/wheels \
  -c results/deployment/company_auxiliary_20260930/preserve-existing.txt \
  -r configs/company_auxiliary_requirements.txt
python -m pip install --no-index --no-deps --force-reinstall \
  --find-links .runtime/cache/wheels opencv-contrib-python==4.10.0.84
python scripts/install_company_auxiliary.py --root /home/work/analysis_code --audit-only
```

以上恢复只涉及已缓存的依赖，不包含模型权重、另行研究的源码仓库或公司数据。
