# cats-videomaev2-finetune Proposal

## Why

cats_v1 当前最优 val top1 仅 67.05%（SlowOnly），距中期验收硬指标 75% 差 8pp；而 K400 复现评测中 VideoMAEv2-base 以 84.71% top1 居 18 个模型之首，比 SlowOnly 起点（75.40%）高 9.3pp。它此前被移出训练 registry 的唯一原因是 mmaction2 官方不提供 train config（能评不能训）——`configs/pet_mammal_videomaev2_base_16x4.py`（commit bc8fcd5）已证明手写 finetune config 可行。现在把它接回训练体系并在 cats 数据集上实测，是 t12 精度攻坚成本最低、上限最高的一步。

## What Changes

- **新增 cats finetune config** `configs/cats_videomaev2_base_16x4.py`：基于 pet_mammal 版改写——cls_head 5 类、backbone `init_cfg=Pretrained(prefix="backbone.")` 从 K710 蒸馏 ckpt 只载 backbone（规避 400 类 head 形状冲突）、AdamW + warmup + cosine 的 ViT 微调配方
- **重新注册 `videomaev2-base`** 进 `server/routers/training.py` 的 `_MMACTION2_REGISTRY`，`mmaction2_config` 指向上述 repo config（`resolve_mmaction2_config` 已支持 repo 根相对路径），web 训练页可选中触发
- **在 pet 上跑通一次训练 + 验证**：GPU 0（现已空闲）执行，记录 val top1 进 `results/training/metrics.json`，产出 cats 基线对比数据
- **同步文档**：修正 cats-dataset-v1 中"VideoMAE 不可训练"的表述（training/using-mmaction2 skill 相关段落）

不改动：`--pretrained` 注入 `load_from` 的整模加载语义（VideoMAEv2 走 config 默认模式，不传 pretrained 标志）；mammal 中间域 config（已在 t12-2 范围）。

## Capabilities

### New Capabilities
- `videomaev2-cats-training`：VideoMAEv2-base 在 cats 数据集上的可训练性与训练产物契约——registry 可选中、config 自带 backbone 预训练加载、训练产出 metrics.json 指标与 checkpoint

### Modified Capabilities

（无——speedrun-results、tools/md-to-docx 的需求不受影响）

## Impact

- **代码**：`configs/cats_videomaev2_base_16x4.py`（新增）、`server/routers/training.py`（registry 加 1 条）、skill 文档微调
- **数据/产物**：pet `results/training/`（新 run 记录 + work_dir checkpoint）、`checkpoints/videomaev2-base/`（已存在，复用）
- **训练执行**：pet GPU 0，batch_size=2、lr=1e-4（ViT 配方，非 API 默认 1e-3）、约 25–30 epochs（528 train clips，估 3–6 min/epoch）
- **风险**：ViT 微调对 lr 敏感，若 30 epoch 内 val top1 不及 SlowOnly 基线，结论本身有价值（排除该路线，聚焦两阶段 mammal 预训练）
