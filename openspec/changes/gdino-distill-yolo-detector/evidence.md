# 实验证据

### 2026-11-07：2.1 环境预检与授权

- **用户授权**：用户批准先用 COCO 预训练权重做延迟探测（不训练、不使用本域数据）。
- **训练框架**：pet 的 `yolo` conda 环境已装 `ultralytics 8.4.120`（`plf`/`pet` 未装）。**无需新装**，因此不触碰 `plf` 主环境。
- **预训练权重已在机器上**，无需下载：`/home/wyy/pet-final/weights/yolo11n.pt`（5,613,764 B）、`yolo11s.pt`（19,313,732 B）。`yolov10` 权重不存在，若纳入对照需另行下载（网络需清掉 pet 上失效的 `http_proxy=127.0.0.1:7890`，直连可用）。
- **容量预检**：`preflight.sh --gpu-index 0` 通过——GPU 0 空闲（util 0%、held 0 MiB），load 0.32/24 核，可用内存 115,307 MiB。
- **硬件**：��
- **许可证**：Ultralytics 为 **AGPL-3.0**。本 change 只做离线训练与评测，不进入交付链路，本轮不触发开源义务；若将来替换生产检测，须先解决许可证（design 4.4 已记录，退路为 Apache-2.0 的 YOLOX / RT-DETR，数据格式与模型无关）。
- **判据达成**：授权、preflight、GPU 型号与空闲显存均已记录。
