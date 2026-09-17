# Design: pet-motion-latent-pipeline

> 所用算法的原理说明见文末「附录 A」，正文按决策组织。

## Context

见 proposal。三条已有资产可复用：① `yolo11-detection-prep` 完成的零样本体检与 Label Studio 预标注（夜视漏检 70%+ 已量化，9 月微调数据标注中）；② `extract_superanimal_keypoints.py` / `convert_keypoints_posec3d.py` 关键点链路；③ 综述 §4.4 数字人 motion latent 架构分析（VASA-1 解耦 / FLOAT identity-motion 分解 / Avatar Forcing 因果生成 / Ditto 工程流水线）。

## Goals / Non-Goals

**Goals:**
- 离线猫居中预处理（检测→跟踪→稳定裁剪→关键点）跑通全部 79 段 + live 录像
- motion latent 提取器训练 + L3 聚类发现 + L1 线性探针评测
- **双模式推理出口**（2026-09-16 用户修订）：① 非实时抽查 CLI ② 实时监控（SSE 流式）；两者**共享同一份行为簇字典**（离线发现 / 在线分配）

**Non-Goals:**
- **7×24 全自动无人值守**（实时模式 = 按需开启的在线推理，不是全时连续监测）
- GroundingDINO 在线化（重模型不挂实时路径；实时路径复用 live 模块流式设施）
- 动作码条件生成（扩散头）——二期

## Decisions

### D5: 环境隔离

GroundingDINO/HQSAM/ViTPose 依赖重且与 mmaction2 的 mmcv 约束冲突风险高 → pet 上新建 conda env `plf`（precision livestock farming），管线脚本以 subprocess + env 切换调用，产物落盘交接（NPZ/pkl），不跨环境 import。

## Risks / Trade-offs

- [AP-10K 关键点域差（已实测裁定，2026-09-14）] → 关键点降级辅助信号，主表示切换视频编码器特征（D8）；关键点 NPZ 仍产出供辅助/消融
- [GroundingDINO 对白天遮挡/猫出画的边界情况] → 插值 + 猫在场率统计（spec 已约束）
- [~~VQ 码本塌缩~~ 已不适用] → 2026-09-17 全面去量化（连续潜变量 + KL 正则），无码本；改为监控「潜空间各向异性 / λ 方差谱」
- [activity 伞类导致聚类簇与人工标签对不齐] → NMI 只作参考指标，簇的语义由人工看代表帧命名；管线目标就是发现更好的类别表
- [三套环境（pet/plf/live）运维复杂] → 每套一个 conda env + README 锁版本；subprocess 交接全部走落盘文件

## Migration Plan

1. 合入脚本与模型代码（本地）→ push pet
2. plf 环境搭建 + 权重下载 → 第 0 关卡（白天关键点质量抽查）
3. 离线管线跑 79 段 → 抽查式 CLI 联调
4. 隐空间训练 + 评测报告
5. 回滚：全部为新增脚本/数据，git revert + 删 env 即可

## Open Questions

- 夜视二期所需的 YOLO11 微调版何时就绪（依赖 9 月标注）→ 不阻塞本 change（白天范围）

### D6: 可替换模块架构（petlib 接口层）

管线代码只依赖抽象接口，具体实现经注册表工厂 + 配置选择——换跟踪器/检测器/关键点提取器 = 改一行配置。

```
petlib/
├── schemas.py      # dataclass: Detection(box,conf,cls) / Track(id,boxes,conf,interp_flags) / KeypointSequence(kp,score,frame_inds,total_frames)
├── detection/      # base.py: Detector.detect(frame)->list[Detection]；grounding_dino.py、yolo11.py
├── tracking/       # base.py: Tracker.update(dets)->list[Track]；byte_track.py、oc_sort.py、bot_sort.py、deep_sort.py
├── keypoints/      # base.py: KeypointExtractor.extract(crop_seq)->KeypointSequence；superanimal.py、vitpose_ap10k.py
├── actions/        # base.py: ActionClassifier.classify(clip)->list[Action]；motion_latent_probe.py（隐码+线性头）、mmaction2_model.py（包装 mmaction2 推理）
├── registry.py     # create_detector/tracker/extractor/classifier(name, **cfg)
└── contract_tests.py
```

**与 mmaction2 的关系**：mmaction2 是 vendored 的 PyTorch 训练/推理框架（OpenMMLab 生态，非 PaddlePaddle），保持 `models/mmaction2/` 只读不动（716 个 py 文件 / 248 个 config，物理移入 petlib 会破坏上游同步、内部 import、config 相对路径与依赖方向四项契约）。petlib 不重新实现动作模型，而是通过 `actions/mmaction2_model.py` 把现有 checkpoint（VideoMAEv2/SlowFast 等）包装为 ActionClassifier 实现——该适配器是**全仓库唯一 import mmaction2 的接触点**，mmaction2 是被接口包装的引擎，不是被迁移的对象；将来换框架只重写这一个适配器。

三条规则：① 管线编排（followcam/spot_check）只 import base 抽象类；② 所有实现输出统一 schema（关键点 NPZ = (T,V,3)+frame_inds 口径，沿用踩坑结论）；③ 契约测试——每个新实现注册后必须通过统一冒烟（fixture 帧→接口调用→schema 校验）。跟踪器/关键点提取器的选型实验（关卡 0 与 1.2b）即在此接口上运行。

---

## 决策索引（物理拆分记录 2026-09-14）

| 决策 | 位置 |
|---|---|
| D1 检测/跟踪/居中工程形态、D2 关键点选型裁定、A1 检测、A3 关键点 | `batch-followcam-extraction/design.md` |
| D1b GatedTracker 否决、D1c 候选跟踪器原理、A4 跟踪 | `tracker-selection/design.md` |
| D2b HQSAM 定位、D3 隐空间架构、D8 主表示选型、A5/A6 隐空间原理 | `video-feature-latent/design.md` |
| D4 推理形态（双模式，2026-09-16 修订）、D7 身份体系、A7 推理头 | `spot-check-cli/design.md` |
| D9 登记-检索架构、A2 分割 | `registry-retrieval/design.md` |
| D5 环境隔离、D6 petlib 接口（跨切面）、Risks/Migration/Open Questions | 本文件（见上） |

**决策 ID 全局唯一且不变**，跨 change 引用按此索引回查。
