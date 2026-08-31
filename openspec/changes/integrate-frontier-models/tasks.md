# Tasks: integrate-frontier-models

## 1. VideoMAE v1 注册

- [x] 1.1 本地 config `configs/pet_mammal_videomae_v1_base_16x4.py`（基于 vendor videomae vit-base K400 预训练 finetune config，覆盖 pet_mammal_v0 数据集与类别数）
- [x] 1.2 权重下载确认（download_checkpoint.py 模式，K400 掩码预训练 ViT-B）
- [x] 1.3 registry 追加 `videomae-v1` 条目（description 注明与 VideoMAEv2 的定位差异：纯 K400 掩码预训练口径）
- [x] 1.4 远端冒烟：1 epoch 最小训练通过

## 2. UniFormerV2 注册

- [x] 2.1 本地 config（vendor uniformerv2 K400 finetune 为基础，覆盖数据集）
- [x] 2.2 权重下载确认（OpenGVLab 官方发布）
- [x] 2.3 registry 追加 `uniformerv2-base` 条目
- [x] 2.4 远端冒烟：1 epoch 通过（重点验证 vendor config 与权重头形状匹配）

## 3. 姿态桥接流水线

- [x] 3.1 `scripts/extract_superanimal_keypoints.py`：SuperAnimal-Quadruped 零样本推理，输出 NPZ（keypoints/scores），幂等 + `--force`
- [x] 3.2 SuperAnimal 27 点 → AP-10K 17 点映射表（`scripts/keypoint_mapping_quadruped.json`）+ 可视化抽查工具（叠加关键点帧，抽 10 段人工确认）
- [x] 3.3 `scripts/convert_keypoints_posec3d.py`：NPZ → PoseC3D npz（keypoint/keypoint_score），输出映射日志
- [x] 3.4（偏差：STGCN++ 需 vendor 内注册自定义骨骼 layout，暂缓；主路线 SlowOnly-keypoint）骨架 config `configs/pet_mammal_posec3d_quadruped.py`（PoseC3D heatmap 管线，17 点口径；备选 STGCN++ keypoint 直输 config `configs/pet_mammal_stgcnpp_quadruped.py`）
- [x] 3.5 registry 追加 `posec3d-quadruped` 条目
- [x] 3.6 远端冒烟：转换产物上 1 epoch 通过（PoseC3D 失败则验证 STGCN++ 回退路径）

## 4. AIM Adapter 微调接入

- [x] 4.1 `configs/aim_modules/`：从 AIM 官方实现迁移 Adapter 模块（空间/时间 Adapter + LSA），`__init__` 注册进 mmaction2
- [x] 4.2 本地 config `configs/pet_mammal_aim_vitb_16x4.py`：K400 预训练 ViT-B + 冻结 backbone（paramwise freeze）+ 仅训 Adapter/头
- [x] 4.3 冻结断言脚本：统计 requires_grad 参数量并打印比例（预期 <10%）
- [x] 4.4 registry 追加 `aim-vitb-adapter` 条目
- [x] 4.5 远端冒烟：1 epoch 通过 + 显存对比记录（vs VideoMAEv2 全量微调）

## 5. 文档与收尾

- [x] 5.1 更新 `papers/docs/research-landscape.md` 附录「接入路线图落地状态」；训练操作说明（含各接入项远端触发命令与已知坑）
- [x] 5.2 验证训练前端正确渲染 4 个新 registry 条目（本地起服务抽查）
- [ ] 5.3 提交（feat: 前缀；config/scripts/registry/文档）
