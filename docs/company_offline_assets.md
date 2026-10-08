# 公司服务器离线模型文件说明

目标：`work@10.33.37.211:/home/work/analysis_code`。准备日期：2026-10-08。
本页说明文件用途和后续离线使用方法；最终下载数量及缺项以
`results/deployment/company_assets_20260930/assets_status.json` 为准。

## 文件位置

下表路径均相对 `/home/work/analysis_code`。

| 用途 | 路径 | 内容 |
|---|---|---|
| MMAction2 | `checkpoints/<model_id>/` | 25 份去重的公共权重，覆盖 27 个有下载地址的注册项；共享权重保留各模型路径和 JSON 元数据 |
| 轻量分类/分割主干 | `checkpoints/torchvision/` | MobileNetV3、ShuffleNetV2、LR-ASPP、DeepLabV3、ResNet |
| 猫存在性/实例分割 | `checkpoints/ultralytics/` | YOLO11 n/s、n/s-seg、n-cls、YOLOv8n 和 n-seg |
| 其他轻量检测 | `checkpoints/yolov5-original-v6/`、`checkpoints/nanodet/` | 原版 YOLOv5n/s；NanoDet-Plus M 320/416 的 checkpoint 与 ONNX |
| 背景移除 ONNX | `.runtime/cache/rembg-models/` | U2-NetP、U2-Net、Silueta、ISNet；安装 rembg 本身不包含这些模型 |
| 背景移除训练 | `checkpoints/u2net-training/` | U2-Net/U2-NetP 的 PyTorch checkpoint；检查主清单中的实际状态 |
| 当前 GroundingDINO 实现 | `checkpoints/grounding-dino-tiny/` | Transformers 格式模型、配置、处理器和词表；固定 HF revision，镜像哈希一致 |
| 原生 GroundingDINO 备用 | `checkpoints/groundingdino-native/` | 原始 Swin-T checkpoint、配置及 `bert-base-uncased/`；与 Transformers 目录的加载方式不同 |
| Rockchip 优化导出 | `checkpoints/rockchip-onnx/` | 官方模型库 YOLO11n/s ONNX；使用优化后的输出及对应后处理 |
| 候选源码 | `third-party/offline/sources/` | 14 个固定 commit 的 ZIP；包括 U2-Net、YOLO、NanoDet、MS-TCN、ASFormer、ASRF、BoxMOT 和 Rockchip 模型库 |
| RV1126B 工具链材料 | `third-party/offline/rknn-toolkit2-2.3.2/` | 官方文档、板端 runtime/header/server、Linux ARM Lite wheel；板端文件只归档 |
| 原环境安装材料 | `.runtime/cache/wheels/`、`.runtime/cache/auxiliary-wheels/` | 既有 156 份缓存 wheel；MMAction2 保留仓库内源码 |
| 新候选依赖 | `.runtime/cache/optional-wheels/` | 19 个固定版本的 wheel/sdist，含 Transformers、tokenizers、pytest、gdown 等；只缓存 |
| 字体 | `.runtime/cache/ultralytics/` | Arial 与 Arial Unicode |
| 全量审计 | `results/deployment/company_assets_20260930/` | manifest、逐项状态、SHA256、来源及下载日志；子目录保存补下载记录 |

源码 ZIP 保留上游许可证和配置，不自动解压安装。U2-Net 训练权重的 Google Drive
来源不可达时使用固定版本的公开社区镜像，校验 HF LFS SHA256；完整版在三个镜像
中的哈希一致。它们没有在本次任务中加载执行。

## 离线入口

从项目根目录启动后，显式设置缓存位置：

```bash
cd /home/work/analysis_code
source .runtime/pet/bin/activate
export TORCH_HOME=/home/work/analysis_code/.runtime/cache/torch
export HF_HOME=/home/work/analysis_code/.runtime/cache/huggingface
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export YOLO_AUTOINSTALL=false
export YOLO_CONFIG_DIR=/home/work/analysis_code/.runtime/cache/ultralytics
export U2NET_HOME=/home/work/analysis_code/.runtime/cache/rembg-models
```

优先传入 checkpoint 的绝对路径。HF 的标准 snapshot/refs 保留在上述缓存中，
也可将加载路径设为 `checkpoints/grounding-dino-tiny/` 并开启 `local_files_only=True`。
Ultralytics 的权重在 `weights/` 保留硬链接，覆盖默认 AMP 自检所需的 `yolov8n.pt`；
这要求从项目根目录运行，或以后显式配置本地权重目录。其他工作目录不要假定缓存
会自动被找到。原生 GroundingDINO 使用本地 BERT 目录时仍需指定其文本编码器路径。

新候选依赖没有安装到工作环境。后续选定具体候选后，从缓存安装并保留核心版本：

```bash
python -m pip install --no-index \
  --find-links .runtime/cache/optional-wheels \
  --find-links .runtime/cache/auxiliary-wheels \
  --find-links .runtime/cache/wheels \
  -c results/deployment/company_auxiliary_20260930/preserve-existing.txt \
  transformers==4.44.2
```

FilterPy、cython-bbox 等若只有 sdist，后续可能需要编译；缓存 sdist 不能当成已编译
wheel。基础 requirements 已与已有版本及待缓存版本核对，extras 和新源码分支另行
核查。`thop` 与 `ultralytics-thop` 共用导入名，不应为备用源码随意覆盖现有 provider。
NanoDet/BoxMOT 等源码的历史接口也需按选定版本适配，不能直接升级核心 Torch/MMCV。

## 核验和续传

只验证文件，不执行模型：

```bash
python scripts/cache_company_assets.py --root /home/work/analysis_code --verify-only
```

获得文件准备授权后，可用以下方式续传；不要与其他写同一清单或同一文件的任务并行：

```bash
python scripts/cache_company_assets.py --root /home/work/analysis_code --retry-failed
```

主清单按文件统计，硬链接别名不会重复计入字节总量。哈希、大小、PDF/ZIP 格式检查
用于确认下载完整性；PyTorch checkpoint 不做 pickle 反序列化。

## 仍需后续工作

公共预训练权重不包含课题组 AnimalKingdom 微调结果，公司数据、标签及训练/验证划分
也需要另行准备。MS-TCN/ASFormer/ASRF 的人类动作权重不能当作猫的边界模型；TCN、
HMM、变化点方法仍需选定特征与标注。定制四足 PoseC3D 注册项没有公开专用权重，
Qwen3-VL-Plus 云服务不能通过文件缓存离线化。板卡 BSP、驱动、系统镜像和真实量化
校准数据需按硬件同事的实际交付确定。

本次只准备文件，没有安装这批可选库，也没有训练、前向、评估、RKNN 构建/模拟或
处理公司数据。文件齐备与文件校验通过，不能代替完整离线运行、精度或板端测速。
