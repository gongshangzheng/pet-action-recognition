# cats-dataset-v1 Tasks

## Phase 1：数据集构建

- [ ] **T1.1** 在 pet 上执行 `scripts/slice_cats_clips.py`
  - 输入：`/home/wyy/mnt/cats/quadruped_cats_v0`（源视频 + annotation JSON）
  - 输出：`/home/wyy/mnt/cats/quadruped_cats_v1/`（clip + manifest）
  - 关键：range 单位是帧（÷15 转秒），标签分配用重叠帧数投票
  - 执行：`ssh pet "source /home/wyy/miniconda3/etc/profile.d/conda.sh && conda activate pet && python ~/pet-action-recognition/scripts/slice_cats_clips.py --root /home/wyy/mnt/cats --output /home/wyy/mnt/cats/quadruped_cats_v1 --clip-length 4 --stride 2 --fps 15"`

- [ ] **T1.2** 创建软链接
  - `ssh pet "ln -sfn /home/wyy/mnt/cats/quadruped_cats_v1 ~/pet-action-recognition/datasets/cats"`
  - 验证：`ssh pet "ls ~/pet-action-recognition/datasets/cats/"` 应看到 classes.txt / videos/ / annotation/

- [ ] **T1.3** 验证数据集
  - clip 数量、split 分布、标签分布是否符合预期
  - 检查 videos/ 目录下文件数量

## Phase 2：代码注册

- [ ] **T2.1** 更新 `server/config.py`
  - 添加 `QUADRUPED_CATS_*` 配置项（参考 `QUADRUPED_ACTION_*` 写法）
  - 路径指向 `datasets/cats`（软链接路径）

- [ ] **T2.2** 更新 `server/routers/training.py`
  - 在 `_DATASET_REGISTRY` 添加 `quadruped_cats_v1` 条目
  - 字段：name / ann_file_* / num_classes=5 / classes_file / data_prefix
  - 确认 `_detect_dataset` 能识别新 dataset name

- [ ] **T2.3** 本地验证
  - 重启后端：`bash start_services.sh` 或 `pkill -f "uvicorn.*8788"; nohup python3 -m uvicorn server.main:app ... &`
  - 访问训练页，确认 quadruped_cats_v1 出现在数据集下拉菜单

## Phase 3：模型训练

- [ ] **T3.1** 训练 videomaev2-base
  - 模式：预训练权重微调
  - 配置：lr=1e-4, batch_size=4, epochs=15

- [ ] **T3.2** 训练 tsm-resnet50
  - 模式：预训练权重微调
  - 配置：lr=1e-3, batch_size=8, epochs=15

- [ ] **T3.3** 训练 slowonly-resnet50
  - 模式：预训练权重微调
  - 配置：lr=1e-3, batch_size=8, epochs=15

- [ ] **T3.4** 训练 timesformer-divst
  - 模式：预训练权重微调
  - 配置：lr=1e-3, batch_size=4, epochs=15

每个训练通过 web 页面或 API 触发，监控训练日志，确保 metrics.json 正确写入。

## Phase 4：结果分析

- [ ] **T4.1** 收集 4 个模型的训练指标
  - top-1 / top-5 准确率
  - best epoch
  - loss 曲线

- [ ] **T4.2** 与 pet_action_mammal_v0 结果对比
  - cats 数据集 vs 哺乳动物数据集的跨域泛化能力
  - 精度差异分析
