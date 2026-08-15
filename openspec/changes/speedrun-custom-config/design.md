# speedrun-custom-config Design

## Context

见 proposal.md - Why。现状代码事实：
- `speedrun.py` 的模型循环基于 `_resolve_models(args.models)`（registry dict：含 `id/config/label_map/type`），checkpoint 全局唯一 `args.checkpoint`，detection 类模型另有分支
- GT 现逻辑：`_gt_from_parent(video)`（UCF101 约定）
- 标注与指标：`scripts/_infer.py infer_and_annotate(video, cfg, ckpt, labels, out_video_path, device, gt_label)` —— 已支持任意 config + gt_label，custom 分支可直接复用
- 推断 config 已生成（上次跑批留下）：`results/training/overrides/inference/{tsm,slowonly,timesformer}-*_infer.py`（5 类，验证过可加载）

## Goals / Non-Goals

**Goals**
- 微调模型走标准管线一次到位（标注/封面/路径/run_name 全对）
- GT 支持 ann_file（覆盖自有数据集场景）
- cats-v1-speedrun 批次用标准管线重跑修复

**Non-Goals**
- API 层 `/api/speedrun/run` 加 custom 字段（等有 Web 触发需求再做）
- registry 结构改动
- speedrun 之外的脚本改动

## Decisions

### D1: `--custom` 用 `model_id=config:ckpt` 重复参数，不引入 manifest 文件
- `--custom tsm-resnet50=/path/a.py:/path/best.pth --custom slowonly-resnet50=...`
- 备选：JSON manifest 文件 → 拒绝，3 个模型 3 个参数足够；文件引入序列化复杂度
- 解析后构造与 registry 同形的 dict（`{id, config, checkpoint, label_map: args.labels 或 --label-map}`），走同一条分类模型分支；id 冲突时 custom 覆盖 registry 条目并 warn

### D2: `--ann-file` + `--label-map` 双参数提供 GT，按 stem 匹配
- ann_file 每行 `<video_path> <label_idx>`（mmaction2 raw label 约定，与 datasets/*/annotation/test_public.txt 一致）
- stem → label_idx → label_map[idx] 类名；装载为 dict，`_gt_for(video)` 先查 dict，miss 回退 `_gt_from_parent`
- 理由：复用现有标注文件格式，零转换；cats 的 `test_public.txt` + `classes.txt` 直接可用

### D3: 重跑用 `--force` 覆盖 outputs/ 旧文件，results.json 记录原地更新
- 结果 id 规则不变（`speedrun-<model>-<stem>`），同 id 覆盖 → 303 条被替换为新记录（带 metrics.top5、新 output_video、run_name 传 `cats-v1-speedrun`）
- 旧 demo.py 视频（无 margin）被同名覆盖；封面在标准管线中自动重抽（covers/ 共享，101 张不变，重抽无害）
- 跑批前备份 results.json（.bak3）

### D4: 批量 3 模型一次进程跑（顺序推理，避免多进程抢 GPU）
- 单条 `python scripts/speedrun.py --videos <101个> --custom ...×3 --ann-file ... --label-map ... --run-name cats-v1-speedrun --force`
- 101×3 视频 × ~3s ≈ 15-20 分钟（标准管线单进程推理比 demo.py 子进程开销小）

## Risks / Trade-offs

- [custom config 加载失败] → 逐模型 try/except，失败记 status=error 不中断整批
- [label_map 顺序与训练时不一致] → 用训练数据集同款 classes.txt（quadruped_cats_v1/classes.txt 即训练 label_map），已在推断 config 验证过一致性
- [重跑覆盖期间页面短暂 404] → speedrun 无并发观众，可接受

## Migration Plan

1. 改 `scripts/speedrun.py`（--custom/--ann-file/--label-map + GT 链 + custom 模型分支）
2. pet 上先 1 模型 × 2 视频烟测（标注格式、GT、correct 正确）
3. 全量 3×101 重跑（备份 results.json → --force）
4. rsync results.json 回本地，页面验证黑 margin + top5 + 准确率
5. 更新 testing skill 文档

回滚：results.json 有 .bak3；outputs 旧视频被覆盖前无单独备份（但 demo.py 版本本就是缺陷产物，无保留价值）。
