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

### D1b: 【已否决方案记录】检测误报门控（DetectionGate）

**事故**：074451 段末尾 GroundingDINO 把沙发误检为猫（conf 过线），argmax 取框 + 线性插值把跳变铺开成可见漂移。

**曾考虑的方案**：检测后门控组件（全候选评分 × 尺寸一致性门 × 运动一致性门 × coast 策略，挂检测器与任意跟踪器之间）。**用户裁决（2026-09-10）：否决**——其两道门与 OC-SORT 的 OCM（速度方向一致性代价）重叠度高、边际优势先验低，且引入额外组件复杂度。

**替代方案（保留执行）**：任务 3.4b 检测器侧误报抑制消融——阈值扫描（0.3/0.4/0.5）× prompt 变体，画漏检率 vs 误报率权衡曲线。若后续高阈值下真猫漏检不可接受、且误报仍造成漂移，门控思想可复活重提（本记录保留上下文）。

### D2: 关键点提取器可插拔——SuperAnimal vs ViTPose 双候选对比（不做先验断言）

两个候选各有依据，**无实验前不预设胜负**：
- SuperAnimal-Quadruped（DeepLabCut 生态，26 点四足专用定义，零样本）
- ViTPose+（AP-10K 动物数据训练变体，AnimalFormer 在羊上验证过）

关卡 0 = 双候选对比实验：同 5 段白天抽帧跑两套，比①置信度分布 ②关键点时序抖动（相邻帧位移方差）③可视化人工抽检。接口做成可插拔（统一输出 NPZ schema），落选者保留为备选。

**✅ 关卡 0B 实测裁定（2026-09-14，用户判定）**：实际执行的候选为 MMPose 生态 HRNet-W32-AP10K 与 ResNet-101-AP10K（SuperAnimal 需 deeplabcut 重依赖未装）。结果：两段验收视频 mean conf 0.33–0.46（crop-first 口径 0.455），可视化人工抽检后**用户判定「关键点连出来了但提取不出信息」**——AP-10K 域在家猫特写上的点位质量不足以作为主表示。**裁定：关键点降级为辅助信号**（在场率/运动强度/簇命名叠加参考），主表示切换为预训练视频编码器特征（见 D8）；SuperAnimal 不再进入主链，域适配微调可作为未来升级路径。

### D2b: HQSAM 的定位——它是什么、能干什么、为什么不在主链

**HQSAM 是什么**：Segment Anything（SAM）的高质量变体——可提示分割基础模型。输入一个框（来自 GroundingDINO），输出**像素级动物轮廓 mask**（精确到毛发边缘，SAM 在细边界上会糊，HQ-SAM 用高质量输出 token + 早晚特征融合修正）。与检测器的区别：检测给"框"（含 60–80% 背景），HQSAM 给"轮廓"（只含动物像素）。

**它在管线里的三个潜在用途**：
1. **mask 清洗 crop（消融实验 3.5）**：把裁剪帧中背景像素抹掉/模糊，只留猫——对抗白天背景捷径学习（模型靠猫砂盆/家具位置猜动作）。是否有效未知，故为消融实验而非主链
2. **体型/毛色分析（二期）**：轮廓面积/脊柱曲率可服务健康监测（消瘦检测），毛色区域可辅助个体识别
3. **关键点质量辅助（弱）**：理论上 mask 可限制关键点搜索区域，但 SuperAnimal 全图推理已够用，收益不明确

**为什么不在主链**：主链表示为视频特征（D8 修订后），mask 是像素级资产，主链没有消费者；且 HQSAM 每帧 ~150-250ms，挂主链白白拖慢管线。结论：主链 = 检测→跟踪→裁剪；HQSAM 独立成可选阶段（按需开启），消融实验决定 mask-cleaned crop 是否成为训练数据的默认形态。

### D3: 隐空间架构（修订版：视频特征主链；VQ 自训降级为可选增强）

**关卡 0B 裁定后的主链（零训练，无新模型训练）**：
```
followcam 视频 ─滑窗(16帧,stride8)─► 预训练编码器(VideoMAEv2/DINOv2) ─► 窗口特征(768d) ─时序平滑─► UMAP+HDBSCAN ─► 行为簇
```
- 窗口特征 = 编码器 CLS token（VideoMAEv2）或逐帧 patch 均值池化+时序池化（DINOv2）
- 主表示选型实验（D8）在两个编码器上同台对比后定主用
- 关键点序列仅作辅助：在场率/运动强度统计、簇代表帧叠加参考

**可选学习版（仅当零训练基线不达标时启动，架构沿用 FLOAT/Keypoint-MoSeq 杂交）**：
```
x = 视频特征窗口 (48,768) ─E_mot(1D CNN+Transformer)─► h(12,256) ─VQ(K=512,d=32)─► z(12,32) ─G─► x̂
L = L1(x,x̂) + 1.0·L1(Δx,Δx̂) + L_vq + 0.1·InfoNCE(s) + 0.01·‖Δz‖²
```
- 输入由原关键点 (48,34) 修订为视频特征序列（48,768），其余不变
- VQ 码本 K=512；码本利用率 <50% 触发重置（防塌缩）
- 身份码对比学习：监督信号 = track 级 ID；参数量目标 <10M；单卡 4090 训练 ≤4h
- 与 Keypoint-MoSeq 的差异：HMM → VQ-VAE/Transformer；关键点 → 视频特征；产出离散 token 便于 L2 切分与统计

**实施次序（修订）**：零训练编码器特征基线 = **主链**，不再是「基线」——若其「人工可命名率 ≥60% 且簇不碎」且线性探针达标，学习版整个不启动

### D4: 抽查式推理为独立 CLI，非 live 模块扩展

用户确认生产形态 = 非实时抽查。CLI `scripts/spot_check_actions.py --camera C --from T --to T`：拉取该时段录像 → 复用预处理管线 → 隐码 → 动作报告（JSON/Markdown）。live 模块零改动。

### D5: 环境隔离

GroundingDINO/HQSAM/ViTPose 依赖重且与 mmaction2 的 mmcv 约束冲突风险高 → pet 上新建 conda env `plf`（precision livestock farming），管线脚本以 subprocess + env 切换调用，产物落盘交接（NPZ/pkl），不跨环境 import。

## Risks / Trade-offs

- [AP-10K 关键点域差（已实测裁定，2026-09-14）] → 关键点降级辅助信号，主表示切换视频编码器特征（D8）；关键点 NPZ 仍产出供辅助/消融
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

### D8: 主表示选型——预训练视频编码器对比实验（关卡 0B 裁定后新增）

**背景**：关键点降级辅助后，主表示 = 跟随视角视频的预训练编码器零训练特征。两个候选：

| 候选 | 机制 | 优势 | 风险 |
|---|---|---|---|
| **VideoMAEv2** | 视频掩码自编码器，时序建模原生 | 动作语义最强（Kinetics 系训练），16 帧窗口直接出 CLS token | 对遮挡/小物体敏感；我们的跟随视频恰好规避这点 |
| **DINOv2** | 图像自监督 ViT，逐帧+时序池化 | 外观/姿态表征稳，逐帧可用（粒度细） | 无时序建模，运动信息靠池化窗口间接获得 |

**实验设计**：两段验收跟随视频 + 抽 3 段其他白天段，两编码器各出窗口特征（16帧窗口 stride8）→ 各做 UMAP 可视化 + 时序平滑度（相邻窗口特征余弦距离分布）→ 人工看簇内代表帧可命名性。**判定：可命名簇比例为主，时序连续性为辅；打平取 VideoMAEv2**（时序原生）。两实现均走 petlib 接口（`petlib/features/`），契约测试复用。

**与评测的关系**：§7 线性探针的「基线」相应改为**同一编码器在原始整帧（未跟随）视频上的特征**——对比的是「跟随预处理是否带来增益」，而非「我们 vs VideoMAEv2」。

### D9: 登记-检索架构（用户确认方向 2026-09-14，实施待批准）

**用户需求（两条，确认为同一机制）**：① 框出猫 → embedding → 检索库中找最相似 → 确定是哪只猫（RAG 式检索）；② 用户拍几张碗的照片 → 模型识别出「这只是碗、其他不是碗」（解决 GroundingDINO 文本检测碗偏掉的问题）。

**统一架构（登记-检索 / Re-ID）**：
```
登记：用户框选/拍照 → DINOv2 embedding → 特征库（FAISS）
      猫登记照 3-5 张/只、物品照片 3-5 张/件
检索：候选区域（GroundingDINO 粗框 / SAM mask）→ DINOv2 embedding → 余弦最近邻
      文本检测管「类别级候选」，登记照管「实例级判定」——两者串联互补，主链不废弃
```

**关键判断**：家庭场景是极端封闭集（2-5 只猫、几件固定物品），DINOv2 零样本 embedding + 最近邻预计够用，**无需训练**；零样本不稳时的兜底 = embedding 上训 logistic 回归小分类器（分钟级）。猫 Re-ID（§8.2 register_cats.py）与物品识别共用同一套登记-检索代码。

**候选生成问题（用户追问：连碗都检测不到怎么办）**：检索必须有候选区域。文本检测失效时，候选来源按优先级：
1. **SAM/SAM2 自动分割**（segment everything）：无类别抠出画面所有物体 mask，彻底绕开词表；**固定机位只需跑一次**，静态物体 mask 缓存复用——碗/摄像头这类不动的东西成本近乎零
2. **OWLv2 图像引导**：照片直接当 query，不经过文字，能检出文本漏检
3. **帧差/背景减除**：固定机位找「新出现/被移动」的物体，触发局部重分割
4. **GroundingDINO LoRA 室内微调**（用户提出的最后手段）：需标注数据 + 训练成本 + 损伤开放词汇能力，仅在 1–3 全失败时启动

**分工架构**：每帧 GroundingDINO 只管**会动的**（猫）；静态物体走「**一次 SAM 分割 + 登记检索 + 帧差变更触发**」。

**实施时机**：调研结论备档；待 §4 验收后用户决定启动。

---

## 延后任务参考资料

- **跟踪器对比选型**（含 D1c 候选跟踪器原理）：已迁至子 change `tracker-selection`
- **登记-检索架构**（D9）：实施任务见总管 tasks §4B，批准后建议同样拆为独立 change

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
