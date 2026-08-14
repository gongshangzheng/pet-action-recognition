# quadruped-cats-v1

## Overview

Cats 视频切段数据集，用于四足动物动作识别模型训练。

**源数据**：
- 原始视频：79 个 mp4，来自崔（22 视频）和蒋（57 视频）
- 原始标注：Label Studio JSON + CSV，标注格式为 `{start, end}`（**帧数**，非秒数），`timelinelabels`
- 路径问题：标注路径为 `/data/upload/8/HASH-event_TS.mp4`，实际文件为 `event_TS.mp4`（hash 被下载工具剥离），需按时间戳匹配

**核心约束**：
- 标注 range 单位为帧（FPS=15），转换公式：`start_sec = start / 15`，`end_sec = end / 15`
- 切段 clip 标签分配：若 clip 与某 range 重叠 ≥1 帧，则 clip 获得该 label；多 label 重叠时按重叠帧数投票
- 仅保留有标签的 clip，无标签 clip 排除

## Data Format

### Source

```
/home/wyy/mnt/cats/
├── dataset_崔/          22 mp4 (hash 前缀已剥离)
├── dataset_蒋/          57 mp4 (hash 前缀已剥离)
├── annotation_崔/        project-8 JSON + CSV
└── annotation_蒋/        project-6 JSON + CSV
```

### Output

```
/home/wyy/mnt/cats/quadruped_cats_v1/
├── classes.txt          5 行：activity / drinking / eating / grooming / prolonged_stationary
├── videos/              所有 79 个原始 mp4（统一存放）
└── annotation/
    ├── train_public.txt   train clip manifest
    ├── val_public.txt     val clip manifest
    └── test_public.txt    test clip manifest
```

### Clip Manifest Format（mmaction2 VideoDataset）

每行：`<相对 data_prefix.video 的路径> <label_int>`

```
videos/clip_0001.mp4 0
videos/clip_0002.mp4 3
...
```

### Label Map

| ID | Label | Description |
|----|-------|-------------|
| 0 | activity | 一般活动 |
| 1 | drinking | 饮水 |
| 2 | eating | 进食 |
| 3 | grooming | 梳理 |
| 4 | prolonged_stationary | 长时间静止 |

## Slicing Specification

### Parameters

| 参数 | 值 | 说明 |
|------|-----|------|
| clip_length | 4s | 与 pet_action_mammal_v0 分布一致 |
| stride | 2s | 50% 重叠，增强样本量 |
| unit | frame | 基于 FPS=15 精确切段 |

### Algorithm

```
FOR each original video:
  fps = 15
  total_frames = video.frame_count
  clip_len_frames = 4 * fps = 60 frames
  stride_frames = 2 * fps = 30 frames

  FOR clip_start = 0; clip_start < total_frames; clip_start += stride_frames:
    clip_end = clip_start + clip_len_frames
    IF clip_end > total_frames: clip_end = total_frames (pad or stop)
    clip_frames = [clip_start, clip_end)

    # Assign label by overlap voting
    overlap_frames_per_label = {}
    FOR each annotation range (ann_start, ann_end, label):
      overlap = intersection(clip_frames, [ann_start, ann_end])
      IF overlap > 0:
        overlap_frames_per_label[label] += overlap_length

    IF overlap_frames_per_label is not empty:
      label = argmax(overlap_frames_per_label)
      save clip to output
```

### Split Ratio

- 有标注视频 69 个 → 切段后全部参与 split
- 比例：train 70% / val 15% / test 15%（按视频级别 split，切段 clip 继承父视频 split）
- random.seed = 42

## File Manifest

### scripts/slice_cats_clips.py

输入：
- `--root`: `/home/wyy/mnt/cats/quadruped_cats_v0`（源目录）
- `--output`: `/home/wyy/mnt/cats/quadruped_cats_v1`（输出目录）
- `--clip-length`: 4（秒）
- `--stride`: 2（秒）
- `--fps`: 15（帧率，固定）

输出：
- 切段后的 clip mp4 文件到 `videos/` 目录
- `annotation/{train,val,test}_public.txt` manifest 文件
- `classes.txt`
- 摘要 JSON（clip 统计）

### 软链接

```bash
ln -s /home/wyy/mnt/cats/quadruped_cats_v1 ~/pet-action-recognition/datasets/cats
```
