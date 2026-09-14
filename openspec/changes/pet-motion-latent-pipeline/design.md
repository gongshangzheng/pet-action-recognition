# Design: pet-motion-latent-pipeline

> 所用算法的原理说明见文末「附录 A」，正文按决策组织。

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
- 跟踪：**对比选型实验**，候选 ByteTrack / OC-SORT / BoT-SORT / DeepSORT + **GatedTracker（门控包装层，见 D1b）**。PigTrack 畜牧基准（`2507.16639`）显示 SORT 系在检测指标上占优，但那是猪圈域——须在本域验证。实验设计：固定同一检测源（GroundingDINO 白天检出），对 3–5 段人工核对过 track_id 的视频小样本 GT，比 IDF1 / IDSW / 轨迹碎片数 / 框平滑度；判定标准（IDF1 优先，碎片与抖动为辅）与结论一并记录。输出 = 平滑轨迹（滑动平均窗口 5 帧）+ track_id + 插值标记

### D1b: GatedTracker——检测后门控包装层（ sofas 误检漂移事故的设计回应）

**事故**：074451 段末尾 GroundingDINO 把沙发误检为猫（conf 过线），argmax 取框 + 线性插值把跳变铺开成可见漂移。

**机制**（包装任意检测器输出，与 ByteTrack 等并列参与选型）：
1. 收集全部 conf≥0.3 候选（不取 argmax）
2. 运动预测：pred = last + vel（vel = 帧间位移 EMA，α=0.4）
3. 逐候选打分 score = conf × (0.3 + 0.7·IoU(b, last)) × gate；两道门：
   - 尺寸门：side/med_side ∈ (0.25, 4.0)
   - 运动门：max|b − pred| < 3×med_side
4. 全部被拒 → 本帧判漏检（coast，插值补全），rejected 检测（帧号/框/ conf）全量落盘
5. 轨迹后处理：漏检线性插值 → **中值滤波(窗5, scipy.ndimage.median_filter)** → 滑动平均(窗5)

**参数与阈值**：velocity gate 3×med_side；面积比 (0.25, 4.0)；med_side 缓慢更新（逐检测 EMA）。

**诚实的先验评估（2026-09-10，用户质疑后修正）**：GatedTracker 的两道门与 OC-SORT 的 OCM（速度方向一致性代价）重叠度高，相对 SORT 系的**边际优势先验较低**；其对付的问题层（检测器误报）的根本解是**检测器侧抑制**（阈值/prompt 扫描/负 prompt/猫数据微调）。定位降级：从"默认组件"降为 **§2 实验候选之一**——与「检测器侧阈值扫描」同台对比（§3 新任务），实验赢了才进管线，输了删除。**失败条件**不变：门控版仍漂移或阈值扫描已足够，均出局；若高阈值导致真猫漏检不可接受而门控保住召回，才保留。

**位置**：`petlib/tracking/gated_wrapper.py`——不是第四种跟踪算法，是任意检测输出的门控后处理层，同样走可插拔接口与契约测试。

### D1c: 候选跟踪器原理（统一框架 + 各家差异）

**共同框架（tracking-by-detection，五候选共享）**：
```
每帧：检测器出框
  → 每条轨迹用卡尔曼滤波（常速模型）预测本帧框
  → 预测框 vs 检测框计算关联代价（IoU / 外观 / 运动方向）
  → 匈牙利算法求最优一对一匹配
  → 匹配上：用检测修正滤波状态；未匹配轨迹：记 lost，连续超限则死亡
  → 未匹配检测：新建轨迹
```
五家的差异全在三个决策点：**关联代价怎么算、低置信度检测怎么处理、轨迹何时死亡**。

| 跟踪器 | 年份 | 核心机制 | 关键创新 | 已知弱点 |
|---|---|---|---|---|
| SORT | 2016 | 卡尔曼 + 纯 IoU 匈牙利匹配 | 极简、极快 | 只用高分检测；遮挡即断 ID |
| **DeepSORT** (DeepOCSORT) | 2017 | SORT + **级联匹配**（越久失配优先级越低）+ **外观 Re-ID 嵌入**（马氏距离+余弦融合） | 外观特征让遮挡后 ID 续上 | Re-ID 模型人体域训练，动物域需重训/退化 |
| **ByteTrack** | 2022 | **两级关联，不丢低分检测**：高分先关联；剩余低分与未匹配轨迹二次关联 | 遮挡边缘的低分检测给轨迹"续命"，低分误报因对不上轨迹被自然过滤；无需 Re-ID 模型 | 依赖检测器置信度校准；纯运动关联 |
| **OC-SORT** | 2022 | **观测中心三修正**：OCM 观测动量（速度方向一致性计入代价）/ OCR 观测重更新（遮挡结束后用新观测回填被污染的状态）/ OTC 跟踪恢复 | 指出"过度信任滤波器"的失败模式，用观测反修滤波 | 简化实现常见；对快速变向仍敏感 |
| **BoT-SORT** | 2022 | ByteTrack + **相机运动补偿 CMC**（帧间全局仿射估计）+ **Re-ID 外观融合**（IoU 与外观自适应加权）+ 轨迹融合 | 工程完成度最高：补偿+融合双保险 | CMC 对固定机位收益≈0；Re-ID 同 DeepSORT 域问题 |
| **GatedTracker**（ours，D1b） | 2026 | 检测后门控：全候选评分 × 尺寸门 × 运动门 × coast | 专治"检测器误报导致的轨迹跳变"（ sofas 事故）；单猫少猫封闭场景 | 不处理多主体 ID 保持；依赖轨迹级中位统计 |

**对本场景的先验判断（待 §2 实验裁决，不作结论）**：家庭单猫白天 + GroundingDINO 检出率高 → 预期 ByteTrack/OC-SORT 足够；多猫段 BoT-SORT 的 Re-ID 融合与 GatedTracker 的门控各有分工（Re-ID 管"谁是谁"，门控管"不跟误报"）。

**实现来源**：五候选统一取自 **BoxMOT**（原 yolo_tracking，维护中的多目标跟踪库，内含上述算法的官方级实现与统一 API）——不用自研简化版（教训见会话记录：自研近似会让选型结论无效）。GatedTracker 为我方自研（因为 BoxMOT 没有检测误报门控这一层），实现于 petlib/tracking/gated_wrapper.py。

**安装注意**：boxmot 依赖较重（pip 全量安装曾 600s 超时）→ 采用 `pip install boxmot --no-deps` + 手动补齐轻依赖（lap/loguru/filterpy 等按 import 报错逐个装），避免其依赖解析升级 torch 破坏 plf 环境。
- 居中裁剪：虚拟摄像机策略 **CameraPolicy 可插拔**（petlib/pipeline/camera_policy.py），三候选。**先行 = `follow_adaptive`**（用户指示：先用不锁定尺寸的方式试结果）：位置尺寸逐帧跟随检测框（×1.2 外扩，AnimalFormer/畜牧常规做法）
  - `follow_adaptive`（先行默认）：实现最简、猫占比恒定（利于关键点/分类模型）
  - `follow_locked`（对照，design 保留）：位置跟随 + 尺寸锁定（初值 = track 前 N 次检出框 P75×1.2，实测示例段 ≈1234px@2880 宽）——假设：保留猫表观尺寸变化 = 距离/接近行为线索；**该假设未经实验验证，由任务 6.6 消融裁决**；保护规则：实际框 > 窗口×0.9 时临时放大防裁切
  - `fixed`（对照组）：位置尺寸全固定——家猫满屋走会丢主体，预期最差，仅作对照
  - 裁决：任务 6.6 三策略产物各训线性探针 + 人工观感抽查，数据定主用
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

---

## 附录 A：所用算法原理速览

> 按管线阶段排列。每个算法回答三件事：是什么/怎么工作/为什么选它。

### A1 检测

**GroundingDINO（白天主检测器）**
- 是什么：开放词汇（open-vocabulary）目标检测器——用**自然语言**指定要找什么（"cat."），不限于训练类别
- 怎么工作：图像侧 Swin Transformer + 文本侧 BERT 双编码器 → **跨模态特征增强器**（图像特征和文本特征互相注意）→ 语言引导的查询选择 → 解码出 (框, 短语) 对。训练数据是 2800 万"图文-框"对（Grounding-20M），模型学会把"文字描述"对齐到"图像区域"
- 为什么选它：零训练检出猫/person/bowl 三类（闭集 YOLO 需要标注微调）；误报问题用 GatedTracker 门控兜住（D1b）

**YOLO11（夜视微调，二期）**
- 是什么：单阶段闭集检测器（backbone-neck-head 一次前向出框），COCO 80 类预训练
- 为什么夜视要用它：COCO 预训练权重 + 少量夜视帧微调即可针对 IR 域校准；快（边缘可部署）。GroundingDINO 夜视退化（文献 + 群养猪论文实测），微调 YOLO 是对策

### A2 分割

**HQ-SAM（可选，mask 清洗消融 8.5）**
- 是什么：Segment Anything Model 的高质量变体。SAM = ViT 图像编码器（SA-1B：1100 万图 11 亿 mask 训练）+ 提示编码器 + mask 解码器，给框/点就输出像素级 mask；HQ-SAM 加一个**高质量输出 token**，融合图像编码器的早期浅层特征（边缘细节）与晚期语义特征，专修 SAM 在细结构上糊边的问题
- 为什么是可选：关键点隐空间不消费 mask（D2b）；消融实验（8.5）决定 mask 清洗背景是否提升下游

### A3 关键点

**SuperAnimal-Quadruped（DLC 生态，候选 1）**
- 是什么：跨物种四足关键点基础模型（DeepLabCut 团队），26 点四足骨架定义
- 怎么工作：DLC 范式 = ImageNet 预训练 CNN + 少量标注帧热图微调 + **主动帧选择**（只标模型最不确定的帧）；SuperAnimal 在大规模多物种动物关键点上预训练，对未见物种**零样本**出点
- 为什么选：对宠物零标注；DeepLabCut 生态十年验证

**ViTPose-AP10K（候选 2）**
- 是什么：纯 ViT 骨干 + 简单反卷积线性头的姿态估计器；AP-10K = 23 科 54 种动物的 17 点关键点基准
- 怎么工作：人体姿态预训练迁移到动物（ViTPose 核心发现：人体姿态知识跨物种可迁移）；AnimalFormer 在羊上用的就是它
- 为什么候选：与 SuperAnimal 是**不同技术路线**（人体迁移 vs 动物原生），谁好用由关卡 0B 实验裁决

### A4 跟踪

SORT/DeepSORT/ByteTrack/OC-SORT/BoT-SORT/GatedTracker 原理见 **D1c**（统一框架 + 逐家机制/创新/弱点表）。

### A5 运动隐空间

**VideoMAE / VideoMAEv2（下游 L1 的骨干来源）**
- 是什么：视频掩码自监督预训练——把视频切块后**遮住 90%**，让模型从稀疏可见块重建被遮内容
- 为什么有效：极高掩码率迫使模型学运动语义而非外观纹理；且**几千段视频即可预训练**（数据效率），V2 的双掩码+蒸馏把规模推到十亿参数级
- 与本项目：训练/评测模块现用的骨干谱系；隐空间线性探针的对照基线

**FLOAT（隐空间架构来源，D3）**
- 是什么：运动隐自编码器——参考帧编码为静态身份码，序列编码为运动隐码，解码重建；流匹配生成
- 借鉴点：identity-motion 分解结构（见 D3）

**VQ 层（离散动作 token）**
- 是什么：VQ-VAE 的离散码本——编码器输出连续向量后，用最近的码本条目替换（直通估计器训练）；码本 = "动作字典"
- 为什么：离散 token 让 L3 聚类/直方图统计天然可做

### A6 无监督行为发现（零训练基线，D3 实施次序）

**UMAP**
- 是什么：流形学习降维——基于模糊单纯集假设，保持数据局部邻接结构，把高维特征投到 2D/低维
- 用途：把运动学特征（速度/关节角/距离）从高维压到低维供聚类

**HDBSCAN**
- 是什么：密度层次聚类——不需要指定簇数 K，自动发现任意形状的簇，并把低密度点标为噪声
- 为什么：行为簇数量未知（不能定 K）、且有噪声帧；HDBSCAN 的"噪声标签"机制天然对应"无法归类的动作"

### A7 推理头

**线性探针（L1 评测）**
- 是什么：冻结特征提取器，只训练最后一层线性分类器
- 为什么：衡量表征质量的标准方法——如果隐空间线性可分到 5 类动作，说明表征真的编码了动作语义；参数量小，小数据不易过拟合

**DINOv2（猫个体识别特征，9.2）**
- 是什么：自监督 ViT 特征（1.42 亿图训练），通用视觉表征
- 为什么：猫个体识别用其特征 + 度量学习/最近邻（借鉴 Label a Herd in Minutes 的自监督配方），避免训练专用 Re-ID 网络
