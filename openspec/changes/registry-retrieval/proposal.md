# Proposal: registry-retrieval

> 子 change，总管：`pet-motion-latent-pipeline`。**状态：延后**——用户已确认方向（2026-09-14），实施待批准。

## Why

两类需求共用同一「登记-检索」机制：① 框出猫 → embedding → 检索确定是哪只猫（猫 Re-ID）；② 拍几张碗/摄像头照片 → 实例级识别（GroundingDINO 文本检测碗实测全误框、camera 召回 4/1859，multi-object-detect-gate 已裁定撤下这两类）。

## What Changes

- 统一登记-检索库：登记照 → DINOv2 embedding → FAISS（猫与物品共用一套抽象）
- 静态物体候选生成：SAM 一次性分割（固定机位缓存 + 定期重分割）+ 帧差变更触发
- 物品实例识别闭环：mask/粗框候选 → DINOv2 检索判定；OWLv2 图像引导作对照；GDINO LoRA 微调仅最后手段备档
- 猫 Re-ID：与 `spot-check-cli` 的 register_cats.py 合并设计

## Capabilities

### New Capabilities

（实施时补 spec delta；当前为延后备档 change）

## Impact

- 预计新增 `petlib/identity/` 抽象 + 登记 CLI；特征库 gitignore
- 前置：video-feature-latent 的 DINOv2 依赖落地后可复用
