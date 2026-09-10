# cats-videomaev2-finetune Design

## Context

见 proposal.md（动机与差距）。技术现状约束：

- mmaction2 vendored 的 videomaev2 config 只有 model + test 段，无 `optim_wrapper/train_dataloader/train_cfg`
- `scripts/train_model.py` 已有两处为此准备的机制：① `_maybe_write_override` 检测到 config 无 `optim_wrapper` 且 backbone 为 ViT 时自动内联 `adam_20e.py` schedule；② 自定义数据集（ann_train/ann_val）走 override Python 文件而非 `--cfg-options`（后者会丢 pipeline）
- `configs/pet_mammal_videomaev2_base_16x4.py`（bc8fcd5）已验证完整 finetune config 写法：backbone `init_cfg=Pretrained(prefix="backbone.")` 只载 backbone，规避 400 类 head 形状冲突；AdamW lr=1e-4 + 5ep warmup + cosine 25ep
- cats 数据集（pet `datasets/cats` → NAS 软链）：`annotation/{train,val,test}_public.txt`（528/88/101 clips，ann 内路径 `videos/event_*.mp4` 相对数据集根），`classes.txt` 5 类；`resolve_dataset_paths("quadruped_cats_v1")` 与 `num_classes_for` 均已支持
- pet GPU 0 空闲（24.5GiB），GPU 1 被占（22.2GiB）；`checkpoints/videomaev2-base/videomaev2-base_pretrained.pth`（K710 蒸馏，173MB）已在 pet

## Goals / Non-Goals

**Goals**
- videomaev2-base 可从 web/API/CLI 触发 cats 微调，config 自带权重初始化
- 一次完整训练 + val top1 指标落盘，与 SlowOnly 67.05% / TSM 62.5% / TimeSformer 59.09% 可比

**Non-Goals**
- 不做 mammal 两阶段预训练（t12-2 范围，mammal config 已存在）
- 不改 `--pretrained` 的 `load_from` 整模加载语义
- 不调优超参矩阵（首轮只验证可行性与量级；调优归 t12-3）

## Decisions

### D1：独立 repo config（`configs/cats_videomaev2_base_16x4.py`），registry 指向它

**备选 A**：registry 指回 mmaction2 vendored test-only config，依赖 train_model 的自动内联 schedule。否决——backbone 预训练加载没有着落（`--pretrained` 注入 `load_from` 是整模加载，mammal 实验证实会触发 head 形状问题），自动 schedule 也非 ViT 微调专用配方。
**备选 B**：不进 registry，纯 CLI 直跑 `tools/train.py`。否决——脱离训练体系（metrics.json、web 可见性、断点续训），且 spec 要求 web 可选。
**选定**：克隆 pet_mammal config 改数据集段（5 类、cats 路径、epochs 30→25）。registry 的 `mmaction2_config` 支持 repo 根相对路径（`resolve_mmaction2_config` 先查 `BASE_DIR/cfg`），一条注册即可。

### D2：训练模式 = config 默认（不传 pretrained/load_from）

config 内 `init_cfg=Pretrained(checkpoint="checkpoints/videomaev2-base/videomaev2-base_pretrained.pth", prefix="backbone.")`。相对路径以训练 cwd（repo 根）解析，pet 上文件已存在。UI/调用侧注意：不要勾选"预训练权重"（那会走 `load_from` 整模路径）。

### D3：超参首轮值

AdamW lr=1e-4（API 默认 1e-3 对 ViT 过大，调用时显式传 1e-4）、batch_size=2（ViT-B 16帧 224px，4090 24G 稳）、epochs=25（528 clips ≈ 264 iter/epoch，估 3–6 min/epoch，全程 <2.5h）、`num_clips_val=1`（val 88 clips，5 clips×3crop 评测太慢且无必要）。warmup 5ep + cosine 到 1e-6（config 内已带，`--cfg-options` 只覆盖 max_epochs/lr/batch_size，param_scheduler 不动）。

### D4：文档同步点

cats-dataset-v1 的 tasks.md T3.0 记录了"VideoMAE 不可训练"；training / using-mmaction2 skill 若有对应表述需加注"videomaev2-base 已通过自写 config 恢复可训练"。

## Risks / Trade-offs

- [ViT 微调 lr 敏感，首轮不收敛或低于 SlowOnly] → 结论仍有价值（快速排除）；config 层面已用 warmup+cosine+grad-clip 降低风险；损失曲线异常时可早停
- [cats split 可能存在泄漏（4s clip stride 2s 相邻重叠）] → 本轮 val top1 只作模型间横向对比（同 split 同协议），绝对值待 t12-1 重切后再认定
- [训练中途 GPU 被抢占] → GPU 0 当前独占空闲；run 可 resume（checkpoint 拆分机制已支持）
- [drinking 仅 9 clips，类别学不动] → 预期行为，不做处理（数据修复归 t12-1）

## Migration Plan

部署 = rsync 代码到 pet + 重启 uvicorn；回滚 = registry 条目删除 + config 文件删除（无数据迁移、无 API 破坏——纯增量注册）。

## Open Questions

- 首轮结果若接近 75%：是否立即扩 epochs / 调 lr 再跑一轮？（由 t12-3 实验矩阵决定，不阻塞本 change）
