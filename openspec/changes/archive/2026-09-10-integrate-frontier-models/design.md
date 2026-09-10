# Design: integrate-frontier-models

## Context

训练栈为 vendored mmaction2（`models/mmaction2/`，**只读**）+ 本地 `configs/`（现有 `cats_videomaev2_base_16x4.py` 等自写 config 先例）+ `server/routers/training.py::_MMACTION2_REGISTRY`（20 族已注册）。训练/推理全部在 pet 远端（2×RTX 4090）。vendor 内 `configs/recognition/videomae|uniformerv2/` 与 `configs/skeleton/posec3d|stgcnpp/` 已存在；AIM 官方实现基于 VideoMAE 框架（Adapter 模块可平移）。

## Goals / Non-Goals

**Goals:**
- 三条路线的接入件全部就位：config、registry 条目、脚本、文档
- 全程遵守 vendor 只读约束，custom_imports 模式挂自定义模块
- 每个接入项都有远端冒烟验证

**Non-Goals:**
- VideoMAE V2 域继续预训练（二期）
- InternVideo2/VideoPrism/V-JEPA 等非 mmaction2 体系模型
- 关键点模型本身的训练（只用 SuperAnimal 零样本推理）

## Decisions

### D1: 本地 config 采用「完整独立文件 + 数据集覆盖」模式

沿用 `cats_videomaev2_base_16x4.py` 先例：复制 vendor config 为起点，覆盖 dataset/ann_file/类别数/数据根，文件放 `configs/` 顶层（或 `configs/<model>/`）。不做跨目录 `_base_` 相对引用（vendor 路径在远端与本地一致，但完整文件可读性更好、与现有先例一致）。

### D2: AIM 以 custom_imports + 独立模块目录接入

新建 `configs/aim_modules/`（`__init__.py` + adapter 实现 + 注册），config 内 `custom_imports = dict(imports=['configs.aim_modules'], allow_failed_imports=False)`。**不改 vendor**；参数冻结用 `optim_wrapper(paramwise_cfg=dict(custom_keys={'backbone': dict(lr_mult=0, freeze=True)}))` + backbone `init_cfg` 加载 K400 预训练 ViT。冻结正确性用冒烟脚本断言（统计 requires_grad 参数量）。

### D3: 姿态桥接走「SuperAnimal 推理 → 自研转换 → PoseC3D 动物口径」

- 关键点提取：脚本封装 DeepLabCut/SuperAnimal-Quadruped 推理（远端 GPU，逐视频 NPZ 输出：`keypoints [T,K,2]` + `scores [T,K]`），幂等（输出存在即跳过，`--force` 重算）
- 转换：以 AP-10K 17 点四足口径为 canon，SuperAnimal 点位做映射表；K 维不一致的点丢弃并打印映射日志
- 骨架 config：PoseC3D 动物变体（heatmap 输入）优先；数据管道用 PoseC3D 的 npz 格式（keypoint/keypoint_score 两数组）
- 风险：SuperAnimal(27点)→17点映射的语义损益 → 首次转换后人工抽 10 个视频可视化关键点叠加帧确认

### D4: registry 追加为纯数据改动

`_MMACTION2_REGISTRY` 列表追加 4 条（videomae-v1、uniformerv2、aim-vitb-adapter、posec3d-quadruped），不改训练 API/前端——前端自动渲染新条目。

### D5: 远端执行闭环

权重下载（download_checkpoint.py 模式）、关键点提取、冒烟训练均在 pet 执行；本地只写代码与配置。冒烟 = 最小 epoch（1）+ 最小子集，通过后再谈正式训练（正式训练属 ops，不在本 change）。

## Risks / Trade-offs

- [SuperAnimal→17点映射语义失真] → 可视化抽查 + 保留原始 27 点 NPZ（转换不破坏源数据）
- [uniformerv2 vendor config 与权重命名不匹配] → 接入前先在远端 dry-run config 加载；权重 URL 以 OpenGVLab 官方 README 为准
- [AIM Adapter 与 vendor 版 mmaction2 API 不兼容] → Adapter 只依赖 timm/ViT 基础算子，不依赖 mmengine 版本特性；若遇 API 冲突，降级为「只训头部 + 部分高层 block 解冻」的简化参数分组（同样满足参数高效目标，在文档记录偏差）
- [PoseC3D heatmap 管线对 17 点动物关键点的分辨率敏感] → 冒烟阶段即验证 loss 收敛曲线，异常时回退 STGCN++（keypoint 坐标直输，无 heatmap）

## Migration Plan

1. 合入 config + 脚本 + registry（本地，git）
2. 远端下载权重 → 冒烟训练逐项通过（videomae-v1 / uniformerv2 / aim / posec3d）
3. 回滚：git revert 即可（registry 纯数据、config 独立文件、vendor 零污染）

## Open Questions

（无——SuperAnimal 权重获取方式在实施时确认：DeepLabCut model zoo 直接下载）
