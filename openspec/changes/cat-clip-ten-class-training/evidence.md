# 证据

### 2026-11-07：整帧基线提前终止（保留为对照）

- 十类整帧训练跑到第 4 轮验证（`Epoch(val) [4]` top-1 75.95%、macro-F1 41.36%、balanced 43.35%）后由守卫终止（`.run/guard/clip_train_20261107.log` 记录 `ended by guard`）；GPU 已释放。
- 该次运行**读的是整帧**，不是裁剪画面：片段索引只有 `video` 与帧范围，检测框未参与输入。因此它不能回答“裁剪是否有效”。
- 产物保留在 `results/cat_clip_v8/train20/`，作为整帧臂的部分基线；4 轮结果不足以与 20 轮裁剪臂直接比较，报告须注明。
- 后续裁剪方案见 change `clip-box-crop-input`。

### 2026-11-08：移交

- 本 change 的已完成结果与未决问题已汇总到 `openspec/changes/cat-pipeline-consolidation`；后续实验从那里推进，本文件保留为过程记录。
