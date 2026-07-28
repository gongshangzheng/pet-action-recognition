---
name: datasets
description: |
  数据集与预训练权重的管理指南。说明 UCF101/四足数据集的下载与组织、per-model label_map、checkpoint 下载、NAS 软链、ann_file 格式。
  触发场景：(1) 下载数据集 (2) 下载预训练 checkpoint (3) 管理 label_map (4) 组织 datasets/ 目录 (5) 了解数据集状态
---

# 数据集与预训练权重管理

## 概览

- `datasets/` 整目录被 `.gitignore`（`/datasets/`）忽略——全部为 runtime/external 数据，不入库。
- 真实大文件存 NAS，从 `datasets/` 软链过去；列表文件（`*_list.txt`、`classes.txt`）运行时生成。
- 数据集 + checkpoint 都在 **pet**（远程训练机），本地不存。`checkpoints/` 同样被 `.gitignore`（`/checkpoints/`）忽略。
- 配置入口：`server/config.py` 的 `QUADRUPED_DATASET_NAME` / `QUADRUPED_DATASET_DIR` / `QUADRUPED_CLASSES_FILE` / `CHECKPOINTS_DIR`。

## NAS 软链

- `/home/wyy/mnt/` 是 CIFS 挂载（NAS @ `192.168.110.4`），pet 可达。
- 大数据集放 NAS，从 `datasets/<name>` 软链到 NAS 子目录，例如 `datasets/ucf101 → /home/wyy/mnt/ucf101/UCF-101`。

## UCF101（人类动作，speed run 验证用）

- 来源：CRCV 官方 `UCF101.rar` → `unrar` 到 `/home/wyy/mnt/ucf101/UCF-101/<class>/v_*.avi`（NAS）。
- 软链：`datasets/ucf101 → /home/wyy/mnt/ucf101/UCF-101`。
- 规模：101 类，13320 视频。
- 用途：K400 预训练模型可在此做 speed run 验证（K400 与 UCF101 有重叠类，如 "playing guitar" / "archery" / "crawling baby"）。

## 四足动作数据集（目标数据集，待收集）

- 目录：`datasets/quadruped_action/`，期望结构：
  ```
  classes.txt                          # 每行一个类别名
  quadruped_action_{train,val,test}_list.txt  # 每行：<相对路径> <label_int>
  videos_{train,val,test}/<name>.mp4
  ```
- 状态：`pending_collection`（无真实数据）。`server/routers/training.py` 的 `_split_has_videos(split)` 检查 `videos_<split>/` 内是否有实际视频文件——有才置 `status=collected`，否则 `pending_collection`。
- 冒烟用合成生成器：`scripts/generate_synthetic_quadruped.py`（默认 2 类 `sit`/`walk`，64×64 mp4，`--root/--train-per-class/--val-per-class/--test-per-class`）。
- 训练入口 `scripts/train_model.py` 等会自动定位上述文件并 `--cfg-options` 覆盖 `ann_file` / `data_prefix.video`；类别数从 `classes.txt` 推断并覆盖 `model.cls_head.num_classes`。

## Label maps（per-model）

label_map 文件在 vendor `models/mmaction2/tools/data/<dataset>/` 下：

| 数据集 | 文件 | 类别数 | 用途模型 |
|---|---|---|---|
| Kinetics-400 | `kinetics/label_map_k400.txt` | 400 | 默认（tsn/tsm/i3d/slowfast/tpn/…，registry 不显式设 `label_map`） |
| Kinetics-700 | `kinetics/label_map_k700.txt` | 700 | slowonly |
| UCF101 | `ucf101/label_map.txt` | 101 | c3d |
| SSv2 | `sthv2/label_map.txt` | — | trn |
| AVA | `ava/label_map.txt` | 60 | 检测类模型（registry 暂无，文件就绪待接） |

- registry（`server/routers/training.py` `_MMACTION2_REGISTRY`）每项的 `label_map` 字段指定该模型用哪个；不设则走 mmaction2 config 默认（多数 K400）。

## ann_file 格式（VideoDataset）

- 每行：`<相对 data_prefix.video 的路径> <label_int>`
- `label_int` = 该类别在 label_map 文件中的 0-indexed 行号。
- 例：`videos_train/walk_001.mp4 1`（`walk` 是 `classes.txt` 第 2 行，label=1）。

## 预训练 checkpoint 下载

- 脚本：`scripts/download_checkpoint.py`
  ```bash
  python3 scripts/download_checkpoint.py --list                       # 列出 registry
  python3 scripts/download_checkpoint.py --model-id tsn-resnet50      # 单个
  python3 scripts/download_checkpoint.py --all                       # 全部
  python3 scripts/download_checkpoint.py --model-id <id> --force     # 强制重下
  ```
- 产物（`checkpoints/`，按 model 分子目录，与 trained 分开）：
  - `checkpoints/<model_id>/<model_id>_pretrained.pth`
  - `checkpoints/<model_id>/<model_id>_pretrained.json`（`type=pretrained`，不被 trained latest/best 扫描收录）
- 镜像回退：openmmlab 直链（pet 可达）；`huggingface.co` URL 自动改走 `hf-mirror.com`（国内镜像）。失败重试 3 次（指数退避）。
- 权重 URL 来自 registry 的 `pretrained_url` 字段。

## 远程注意事项

- 所有数据集与 checkpoint 在 pet 上跑训练/推理时使用，本地仓库不持有。
- 远程操作（SSH、conda、端口转发、GPU 共享）见 `remote-servers` skill。
