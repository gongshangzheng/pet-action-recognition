# cats-dataset-v1 Design

## 1. 切段脚本

### scripts/slice_cats_clips.py

**核心逻辑**：
- 遍历 `dataset_崔/` + `dataset_蒋/` 所有 mp4
- 统一复制到 `videos/` 目录（去重，按 timestamp 命名）
- 解析两个 annotation JSON，按时间戳匹配视频
- 按 clip_length=4s, stride=2s 切段
- range 单位转换：`ann_frames / 15 = ann_seconds`
- 标签分配：重叠帧数投票

**依赖**：cv2（opencv-python）

**执行方式**：
```bash
python scripts/slice_cats_clips.py \
  --root /home/wyy/mnt/cats \
  --output /home/wyy/mnt/cats/quadruped_cats_v1 \
  --clip-length 4 \
  --stride 2 \
  --fps 15
```

**输出示例**：
```
quadruped_cats_v1/
├── videos/
│   ├── video_name_ts_0001.mp4   (clip 1)
│   ├── video_name_ts_0002.mp4   (clip 2)
│   └── ...
├── annotation/
│   ├── train_public.txt
│   ├── val_public.txt
│   └── test_public.txt
└── classes.txt
```

### Clip 命名策略

`{original_name_no_ext}_{clip_index:04d}.mp4`
例：`event_20260806_120311_0001.mp4`（第 1 个 clip）

## 2. 配置注册

### server/config.py

```python
QUADRUPED_CATS_ROOT = QUADRUPED_BASE_DIR / "cats"   # 软链接路径
QUADRUPED_CATS_VIDEO_PREFIX = QUADRUPED_CATS_ROOT   # data_prefix.video
QUADRUPED_CATS_CLASSES_FILE = QUADRUPED_CATS_ROOT / "classes.txt"
```

### server/routers/training.py

在 `_DATASET_REGISTRY` 添加：
```python
"quadruped_cats_v1": {
    "name": "Quadruped Cats v1",
    "ann_file_train": "annotation/train_public.txt",
    "ann_file_val": "annotation/val_public.txt",
    "ann_file_test": "annotation/test_public.txt",
    "num_classes": 5,
    "classes_file": "classes.txt",
    "data_prefix": "datasets/cats",   # 软链接路径
},
```

## 3. 模型选择（基于现有结果）

### 现有训练结果（pet_action_mammal_v0，Top-1 Acc）

| 模型 | Top-1 | Top-5 | 状态 |
|------|-------|-------|------|
| videomaev2-base | 0.843 | 0.981 | ✅ |
| swin-tiny | 0.745 | 1.000 | ✅ |
| timesformer-divst | 0.731 | 0.981 | ✅ |
| videomae-base | 0.699 | 0.991 | ✅ |
| slowonly-resnet50 | 0.718 | 0.977 | ✅ |

### Speed Run 结果（RTF 推理速度，显存）

| 模型 | Acc | RTF | GPU MB | 备注 |
|------|-----|-----|--------|------|
| tsm-resnet50 | 100% | 0.13 | 1154 | 轻量高速 |
| c2d-resnet50 | 100% | 0.12 | 3032 | 轻量 |
| videomaev2-base | 100% | 0.19 | 4657 | 精度最高 |
| slowonly-resnet50 | 100% | 0.14 | 2098 | 均衡 |
| timesformer-divst | 100% | 0.22 | 830 | 显存最低 |

### 精选 4 模型

目标：覆盖高精度 + 轻量高速 + 均衡三类

| # | 模型 | 选择理由 |
|---|------|----------|
| 1 | **videomaev2-base** | 现有最高精度（0.843），cats 迁移学习首选 |
| 2 | **tsm-resnet50** | 速度最快（RTF=0.13），轻量，适合实时场景 |
| 3 | **slowonly-resnet50** | 高精度（0.718）+ 速度快（RTF=0.14）+ 显存合理 |
| 4 | **timesformer-divst** | 精度尚可（0.731）+ 显存最低（830MB），边缘部署友好 |

**排除**：
- swin-tiny：精度高但 speedrun acc=0%（模型可能有问题）
- mvit-small / x3d-xs / uniformer-base：反复训练失败，不引入新问题

### 训练配置

| 参数 | 值 |
|------|-----|
| 训练 epochs | 15 |
| 优化器 | AdamW |
| 初始 lr | 1e-4（videomaev2）/ 1e-3（其他） |
| Batch size | 4（videomaev2）/ 8（其他） |
| Weight decay | 0.05 |
| 验证策略 | best top-1 acc |
| 断点续训 | 支持（从 latest.pth 恢复） |

## 4. 目录结构

```
/home/wyy/mnt/cats/
├── quadruped_cats_v0/          # 原始视频 + JSON 标注（保留）
└── quadruped_cats_v1/          # 新增：切段后数据集
    ├── classes.txt
    ├── videos/
    │   └── *.mp4              # 所有 clip
    └── annotation/
        ├── train_public.txt
        ├── val_public.txt
        └── test_public.txt

~/pet-action-recognition/datasets/
└── cats → /home/wyy/mnt/cats/quadruped_cats_v1   # 软链接
```
