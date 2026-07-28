---
name: datasets
description: |
  数据集与预训练权重的管理指南。说明 UCF101/四足数据集/pet_action_mammal_v0 的下载与组织、per-model label_map、checkpoint 下载、软链（NAS 或本地）、ann_file 格式。
  触发场景：(1) 下载数据集 (2) 下载预训练 checkpoint (3) 管理 label_map (4) 组织 datasets/ 目录 (5) 了解数据集状态
---

# 数据集与预训练权重管理

## 概览

- `datasets/` 整目录被 `.gitignore`（`/datasets/`）忽略——全部为 runtime/external 数据，不入库。
- 真实大文件存 NAS，从 `datasets/` 软链过去；列表文件（`*_list.txt`、`classes.txt`）运行时生成。
- 数据集 + checkpoint 都在 **pet**（远程训练机），本地不存。`checkpoints/` 同样被 `.gitignore`（`/checkpoints/`）忽略。
- 配置入口：`server/config.py` 的 `QUADRUPED_DATASET_NAME` / `QUADRUPED_DATASET_DIR` / `QUADRUPED_CLASSES_FILE` / `CHECKPOINTS_DIR`。

## 软链约定

- **NAS 挂载**：`/home/wyy/mnt/` 是 CIFS 挂载（NAS @ `192.168.110.4`），pet 可达；大数据集放 NAS，从 `datasets/<name>` 软链到 NAS 子目录。
- **pet 本地**：`~/datasets/` 是 pet 机器本地磁盘上的数据集目录（不走 NAS），同样从 `datasets/<name>` 软链过去。
- 统一模式：`ln -s <绝对路径> datasets/<name>`，软链只对 pet 生效（绝对路径，本地 mac / A100 上是断链，别在本地依赖）。
- 现有软链：
  - `datasets/ucf101 → /home/wyy/mnt/ucf101/UCF-101`（NAS）
  - `datasets/pet_action_mammal_v0 → /home/wyy/datasets/pet_action_mammal_v0`（pet 本地）

## UCF101（人类动作，speed run 验证用）

- 来源：CRCV 官方 `UCF101.rar` → `unrar` 到 `/home/wyy/mnt/ucf101/UCF-101/<class>/v_*.avi`（NAS）。
- 软链：`datasets/ucf101 → /home/wyy/mnt/ucf101/UCF-101`。
- 规模：101 类，13320 视频。
- 用途：K400 预训练模型可在此做 speed run 验证（K400 与 UCF101 有重叠类，如 "playing guitar" / "archery" / "crawling baby"）。

## pet_action_mammal_v0（项目自有，哺乳动物动作）

- 来源：项目 `data/pet_action_v0` 的严格哺乳动物子集（筛选规则：`species_parent_class` 全部为 `Mammal`；混合类如 `Mammal|Reptile` 一律剔除）。父级 14938 段里选了 2234，剔了 12704。
- 实体位置：pet 本地 `~/datasets/pet_action_mammal_v0/`（不走 NAS）。
- 软链：`datasets/pet_action_mammal_v0 → /home/wyy/datasets/pet_action_mammal_v0`。
- 重建脚本：`python scripts/build_pet_action_mammal_v0.py`（项目根目录）。
- 结构：
  ```
  datasets/pet_action_mammal_v0/
  ├── README.md / SHA256SUMS.txt
  ├── annotation/   # train_public.txt / val_public.txt / test_public.txt 等（MMAction2 VideoDataset manifest）
  └── dataset/video/*.mp4   # 2234 个视频（922 MB）
  ```
- 规模：2234 视频，划分 train 1801 / val 216 / test 217。
- 类别：7 个训练类（`num_classes=7`）—— `0 locomotion`(1276) / `1 jump`(144) / `2 eating`(281) / `3 drinking`(26) / `4 grooming`(37) / `5 still_rest`(310) / `6 social_interaction`(160)。`7 other_unknown` 是保留类，0 样本，**不要用 num_classes=8**。
- MMAction2 接入：
  - `data_prefix = datasets/pet_action_mammal_v0`
  - `ann_file = datasets/pet_action_mammal_v0/annotation/{train,val,test}_public.txt`（manifest 路径形如 `dataset/video/AAABBBBB.mp4 0`，相对 `data_prefix`）
  - `num_classes = 7`
- 注意：片段**未经人工视觉复核**（物种/动作歧义/字幕水印都没人看过），继承父版本 `not_visually_reviewed` 标志。

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
