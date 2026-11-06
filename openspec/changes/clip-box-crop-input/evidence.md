# 证据

### 2026-11-07：跟踪脚本改名，单目标视频同样使用

- **问题**：片段引用的 2,335 个视频里绝大多数是单目标（每帧一个框），但仍要跑跟踪才能得到逐帧框序列；脚本名 `track_multi_pet.py` 描述的是多宠物场景，与实际用途不符。
- **改名**：`scripts/track_multi_pet.py` → `scripts/track_pet_targets.py`，docstring 说明“同样用于单目标视频，每帧一个框得到的是一条普通轨迹”。同步修改 `.claude/skills/cat-pipeline/SKILL.md`、`openspec/changes/multi-pet-track-cropping/*`、`openspec/changes/clip-box-crop-input/tasks.md` 与测试导入。
- **为什么不给单目标另写一条路径**：跟踪器在同一份缓存上对单目标就是“一条轨迹 + 插值”，与多目标共用同一套 IoS 去重、生命周期与放弃规则，避免两套行为漂移。
- **既有失败（与改名无关）**：`tests/test_multi_pet_tracking.py` 两个用例报 `KeyError: 'properties'`，原因是 `petlib/tracking/anchors.py` 在 commit `0ee13b0` 起读取 `payload["properties"]["width"/"height"]`，而测试夹具没有补该字段。属既有夹具缺口，未在本 change 修。

### 2026-11-07：确认现有片段全部为单宠物

- 核对方式：把 `slices_v8/intervals.jsonl` 中 `reason == multi_pet` 的 482 个 `sample_id` 与 `clips.jsonl` 的 7,554 个 `sample_id` 取交集，结果为 **0**。
- 结论：多宠物区间在切片之前就被排除，`slices_v8` 的片段**全部是单宠物**；此前写的“7,072 / 7,554”是错误推断，已更正。
- 影响：本轮训练数据无需再做筛选；多宠物片段要等 `multi-pet-track-cropping` 的标签归属与审阅完成后才能加入。
