# Design: pet-motion-latent-pipeline

## Context

见 proposal。三条已有资产可复用：① `yolo11-detection-prep` 完成的零样本体检与 Label Studio 预标注（夜视漏检 70%+ 已量化，9 月微调数据标注中）；② `extract_superanimal_keypoints.py` / `convert_keypoints_posec3d.py` 关键点链路；③ 综述 §4.4 数字人 motion latent 架构分析（VASA-1 解耦 / FLOAT identity-motion 分解 / Avatar Forcing 因果生成 / Ditto 工程流水线）。

## Goals / Non-Goals

**Goals:**
- 离线猫居中预处理（检测→跟踪→稳定裁剪→关键点）跑通全部 79 段 + live 录像
- motion latent 提取器训练 + L3 聚类发现 + L1 线性探针评测
- 抽查式推理 CLI（非实时），输出结构化动作报告

**Non-Goals:**
- live 实时路径改动（保持现状：YOLO11 + 轻量头）
- 7×24 连续监测；GroundingDINO 在线化
- 动作码条件生成（扩散头）——二期

## Decisions

### D1: 检测/跟踪/居中的工程形态

- 检测：GroundingDINO 开放词汇检出（白天段，零训练）；低置信帧 → 跟踪器插值并打「低置信」标（YOLO11 夜视微调版为二期，本 change 不做）
- 跟踪：**对比选型实验**，候选 ByteTrack / OC-SORT / BoT-SORT / DeepSORT。PigTrack 畜牧基准（`2507.16639`）显示 SORT 系在检测指标上占优，但那是猪圈域——须在本域验证。实验设计：固定同一检测源（GroundingDINO 白天检出），对 3–5 段人工核对过 track_id 的视频小样本 GT，比 IDF1 / IDSW / 轨迹碎片数 / 框平滑度；判定标准（IDF1 优先，碎片与抖动为辅）与结论一并记录。输出 = 平滑轨迹（滑动平均窗口 5 帧）+ track_id + 插值标记
- 居中裁剪：虚拟摄像机策略 **CameraPolicy 可插拔**（petlib/pipeline/camera_policy.py），三候选 + 消融实验裁决（任务 6.6）：
  - `follow_locked`（默认）：位置连续跟随 + 尺寸锁定（初值 = track 前 N 次检出框 P75×1.2，实测示例段 ≈1234px@2880 宽）；保留猫表观尺寸变化 = 距离/接近行为线索；保护规则：实际框 > 窗口×0.9 时临时放大防裁切残肢（事件记入轨迹 JSON，放大次数本身即"猫靠近摄像头"信号）
  - `fixed`：位置尺寸全固定——仅当猫活动区域可预测时可用；家猫满屋走会丢主体，作对照组
  - `follow_adaptive`：位置尺寸全跟随（猫恒定占比）——尺度线索被抹掉 + 框噪声放大为画面呼吸，作对照组
  - 原理：位置 = 干扰项（必须跟随消除），尺寸 = 距离信号（应保留）——"位置跟、尺寸锁"非折中而是信息论正确的分工；最终以消融实验（各策略产物训线性探针）裁决
- 跟踪的四个作用（身份连续/漏检补全/平滑/检测节流）写入 spec 的原因：它们是可验收行为，不是实现细节

### D2: 关键点提取器可插拔——SuperAnimal vs ViTPose 双候选对比（不做先验断言）

两个候选各有依据，**无实验前不预设胜负**：
- SuperAnimal-Quadruped（DeepLabCut 生态，26 点四足专用定义，零样本）
- ViTPose+（AP-10K 动物数据训练变体，AnimalFormer 在羊上验证过）

关卡 0 = 双候选对比实验：同 5 段白天抽帧跑两套，比①置信度分布 ②关键点时序抖动（相邻帧位移方差）③可视化人工抽检 ④各自关键点训隐空间后的 5 类线性探针 top1。决策标准：探针 top1 为主、抖动与抽检为辅；平手则取 SuperAnimal（DLC 生态与现有脚本兼容）。接口做成可插拔（统一输出 NPZ schema），落选者保留为备选。

### D2b: HQSAM 的定位——它是什么、能干什么、为什么不在主链

**HQSAM 是什么**：Segment Anything（SAM）的高质量变体——可提示分割基础模型。输入一个框（来自 GroundingDINO），输出**像素级动物轮廓 mask**（精确到毛发边缘，SAM 在细边界上会糊，HQ-SAM 用高质量输出 token + 早晚特征融合修正）。与检测器的区别：检测给"框"（含 60–80% 背景），HQSAM 给"轮廓"（只含动物像素）。

**它在管线里的三个潜在用途**：
1. **mask 清洗 crop（消融实验 3.5）**：把裁剪帧中背景像素抹掉/模糊，只留猫——对抗白天背景捷径学习（模型靠猫砂盆/家具位置猜动作）。是否有效未知，故为消融实验而非主链
2. **体型/毛色分析（二期）**：轮廓面积/脊柱曲率可服务健康监测（消瘦检测），毛色区域可辅助个体识别
3. **关键点质量辅助（弱）**：理论上 mask 可限制关键点搜索区域，但 SuperAnimal 全图推理已够用，收益不明确

**为什么不在主链**：关键点隐空间只消费坐标 (T,V,3)，mask 是像素级资产，主链没有消费者；且 HQSAM 每帧 ~150-250ms，挂主链白白拖慢管线。结论：主链 = 检测→跟踪→关键点；HQSAM 独立成可选阶段（按需开启），消融实验决定 mask-cleaned crop 是否成为训练数据的默认形态。

### D3: 隐空间架构（FLOAT/Keypoint-MoSeq 杂交，数字人工具 + 行为学目标）

```
x (48,34) ─E_mot(1D CNN+Transformer)─► h(12,256) ─VQ(K=512,d=32)─► z(12,32) ─G─► x̂
x ─E_id(池化+MLP)─► s(64)
L = L1(x,x̂) + 1.0·L1(Δx,Δx̂) + L_vq + 0.1·InfoNCE(s) + 0.01·‖Δz‖²
```
- VQ 码本 K=512：离散 token 是 L3 聚类/直方图的基础；码本利用率 <50% 触发重置（防塌缩）
- 身份码对比学习：监督信号 = **track 级 ID**（跟踪器输出；单猫视频退化为源视频 ID）。注意：不能用视频级 ID 监督多猫段（会把不同猫拉进同一身份码）
- 窗口 48 帧 stride 24；参数量目标 <10M；单卡 4090 训练 ≤4h
- 与 Keypoint-MoSeq 的差异：HMM → VQ-VAE/Transformer；实验室小鼠 → 家庭宠物监控；且产出离散 token 便于 L2 切分与统计

**实施次序：零训练基线先行（B-SOiD 式）**。管线两段性质不同：段 1 关键点提取（SuperAnimal）是预训练模型直接推理、无需训练；段 2 动作隐空间需要自监督训练——但训练在基线不达标时才启动：
- **基线 v0（零训练，先行）**：关键点 → 手工运动学特征（逐帧速度/关节角/成对距离）→ UMAP+HDBSCAN 聚类 → 行为簇。无神经网络训练，一天可跑通，作为后续一切对比的基准
- **学习版（上方 VQ-VAE 主体）**：仅当基线 v0 的「人工可命名率 <60%」或簇碎片化严重时启动；启动后与基线 v0 同台对比（同一评测协议）

### D4: 抽查式推理为独立 CLI，非 live 模块扩展

用户确认生产形态 = 非实时抽查。CLI `scripts/spot_check_actions.py --camera C --from T --to T`：拉取该时段录像 → 复用预处理管线 → 隐码 → 动作报告（JSON/Markdown）。live 模块零改动。

### D5: 环境隔离

GroundingDINO/HQSAM/ViTPose 依赖重且与 mmaction2 的 mmcv 约束冲突风险高 → pet 上新建 conda env `plf`（precision livestock farming），管线脚本以 subprocess + env 切换调用，产物落盘交接（NPZ/pkl），不跨环境 import。

## Risks / Trade-offs

- [白天段 SuperAnimal 关键点质量未验证（低风险）] → 管线第 0 关卡保留：抽 5 段白天可视化抽查
- [GroundingDINO 对白天遮挡/猫出画的边界情况] → 插值 + 猫在场率统计（spec 已约束）
- [VQ 码本塌缩] → 利用率监控 + 重置机制（spec 已约束）
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

### D7: 身份体系——"这是哪只猫"的三层答案

| 层 | 时间范围 | 负责者 | 原理 |
|---|---|---|---|
| 帧内 | 单帧 | 检测器（GroundingDINO/YOLO11） | 检出几只猫、各在什么位置 |
| 轨迹内（秒~分钟） | 连续段 | 跟踪器 track_id（ByteTrack 等） | 外观+运动关联，保证序列内是同一只；无学习 |
| 跨段/跨天（真·识别） | 永久 | **猫个体档案 + 检索式 Re-ID** | 登记照（每猫 3–5 张清晰图）→ 特征（DINOv2/SuperAnimal 外观特征）→ 度量学习 embedding → 新 crop 最近邻检索 |

**借鉴来源（畜牧已验证）**：BMCTrack-d（`2609.03463`，猪背花纹 Re-ID——猫花纹更独特，天然适配）；Label a Herd in Minutes（`2204.10905`，自监督+度量学习+主动学习，10 分钟标注全场）；AutoCattloger（`2508.15945`，登记档案+流式检索）；ReCowGnition（`2607.22071`，封闭群脸识别基准）。

**关键洞察**：家庭是**极端 closed-set**（2–5 只，远小于牧场几十头）——识别是"小规模检索"而非开放集分类，登记照+最近邻已足够；z_id（隐空间身份码）只作与视觉 Re-ID 融合互验的辅助信号，不作主依据（其判别性无保证，见 D3）。
