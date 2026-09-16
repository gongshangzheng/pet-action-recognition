# Design: docs-repo-inventory

## Context

文档现状（2026-09-16 盘点）：

| 位置 | 文件 | 状态 |
|---|---|---|
| `management/docs/`（wiki，9 篇） | mmaction2-overview(183行)、model-onboarding(145行)、keypoint-extraction-pitfalls(142行)、third-party-remix-petra(131行)、live-realtime-inference-plan(118行)、live-page-integration-plan(115行)、detection-annotation-taxonomy(98行)、third-party-pet-videos(108行)、tasks(30行) | 多数活跃；live 两篇已落地；tasks.md 停在 7 月 |
| `docs/plans/`（2 篇） | 2026-07-13 mmaction2 训练集成计划、2026-08-15 二期研究计划 | 前者已落地；后者部分过时（P0 已完成大半） |
| `docs/` | 宠物动作识别研究计划.docx（二进制） | 保留 |
| 根目录 | README.md（118 行） | 缺 training/live/speedrun/pipeline 等半数模块说明 |
| 各子目录 | datasets/quadruped_action/README.md、management/README.md、templates/README.md 等 | 有效目录说明，保留不动 |

散落的知识源（新文档必须收录但现存文档没有的）：`results/` 各 json/md 里的指标与结论、openspec 总管 change（pet-motion-latent-pipeline design 裁决 D1–D9 + 7 个子 change 的任务进度/验收闸门）、训练 run 记录（metrics.json 5 个 run）、批处理报告（batch_report.md 三率+告警结案）。

Wiki 机制（`server/routers/management.py`）：递归扫描 `management/docs/**/*.md`，解析 YAML frontmatter（title/author/date/tags/summary/id），slug=文件名（限 `^[a-zA-Z0-9_/-]+$`），按数字 id 升序、无 id 者按日期倒序排后。现存 9 篇均无 id 字段。

与现有知识库的分工：`.claude/skills/`（15 个）是 agent 操作指南、`AGENTS.md` 是 agent 仓库纪律、wiki 是**人读的项目知识沉淀**——三者不互相复制内容，wiki 用链接引用 skills。

## Goals / Non-Goals

**Goals**
- 一份《仓库资产盘点》作为全库唯一入口，回答"有什么重要内容/数据、在哪、什么状态"
- 一套主题统一、带 frontmatter、id 有序的 wiki 文档（10 篇），吸收全部现存文档的有效信息；其中：**算法架构**一篇专讲全链路设计（定位追踪→动作识别→身份提取→应用出口，每阶段算法+理由），**规划与进度**一篇对未来计划做分类说明（主线执行序/条件启动/研究型/已归档）
- 一份《交接与协作指南》，使新协作者不依赖口口相传即可自主上手（交接包）
- 每篇被删/被吸收文档有明确"信息去向"记录，重要信息零丢失

**Non-Goals**
- 不清理顶层散落文件（另立 change `chore-toplevel-cleanup` 处理），仅在盘点文档登记
- 不改任何代码、数据库、数据集、results 产物
- 不动 `.claude/skills/`、`AGENTS.md`、`openspec/` 本体
- 不整理 management/ 下日报/周报/会议等结构化业务数据

## Decisions

### D1 文档集落位与命名

统一放 `management/docs/`（web Wiki 页自动可见）。文件名 ASCII kebab-case（slug 正则限制），frontmatter 必带 `id: 1..10` 使新文档排 wiki 最前。

### D2 目标文档集总览（10 篇）

| id | 文件 | 标题 | 一句话定位 | 主要来源 |
|---|---|---|---|---|
| 1 | repo-inventory.md | 仓库资产盘点 | 全库唯一入口：有什么/在哪/什么状态 | 新写（D4.1） |
| 2 | datasets.md | 数据集全景 | 当前所有数据集：规模/标注/位置/状态/用途 | 新写 + detection-annotation-taxonomy 全文 |
| 3 | models.md | 模型 | 重要模型逐个条目：简介 + 实测结果 | 新写 + model-onboarding + results/*.json |
| 4 | training-guide.md | 训练体系 | 怎么训：mmaction2 机制/四模式/registry/远程闭环 | mmaction2-overview + model-onboarding + 2026-07-13 计划 |
| 5 | live-module.md | Live 模块 | 落地后架构与关键决策 | 两篇 live plan |
| 6 | algo-architecture.md | 算法架构 | 全链路算法设计：定位追踪→动作识别→身份提取→应用出口，每阶段算法+理由 | openspec 总管/各子 change design（决策 D1–D9 索引） |
| 7 | pipeline-roadmap.md | 规划与进度 | 未来计划四分类：主线序/条件启动/研究型/已归档 + 闸门与二期对照 | 总管 tasks §2/§4 + 2026-08-15 计划 |
| 8 | lessons.md | 研究结论与踩坑 | 关键点五大问题/标注体系教训/用户裁定时间线 | keypoint-extraction-pitfalls + change 裁决记录 |
| 9 | third-party-notes.md | 第三方项目借鉴 | 每个项目八节模板（D5） | 两篇 third-party 文档 |
| 10 | handover-guide.md | 交接与协作指南 | 新协作者上手入口 | 新写（D7） |

### D3 逐篇去留决策表（删除的唯一依据）

| 现有文档 | 评估 | 处置 | 信息去向 |
|---|---|---|---|
| mmaction2-overview.md | 活跃参考 | 吸收后删 | 模型族详解→3，训练链路/四模式→4 |
| model-onboarding.md | 活跃参考（9-16 仍更新） | 吸收后删 | registry/checkpoint/接入→3、4 |
| detection-annotation-taxonomy.md | 活跃参考 | 吸收后删 | 全文→2 |
| live-page-integration-plan.md | 已落地 | 吸收后删 | →5 |
| live-realtime-inference-plan.md | 已落地 | 吸收后删 | →5 |
| keypoint-extraction-pitfalls.md | 活跃研究结论 | 吸收后删 | 全文→7 |
| third-party-pet-videos.md | 借鉴笔记 | 吸收后删 | →8 |
| third-party-remix-petra.md | 借鉴笔记 | 吸收后删 | →8 |
| tasks.md（wiki） | 过时 | 直接删 | 3.2 核对无独有信息后弃 |
| docs/plans/2026-07-13-….md | 已落地 | 吸收后删 | →4 历史决策节 |
| docs/plans/2026-08-15-phase2-….md | 部分过时 | 吸收后删 | →6 |
| docs/宠物动作识别研究计划.docx | 二进制 | **保留原位** | 仅在 1 中登记 |
| README.md | 过时 | **重写** | 模块总览+指向 1 |
| 各子目录 README | 有效 | 保留不动 | — |

### D4 每篇内容规格（逐节 outline，写作时的验收标准）

#### 4.1 repo-inventory.md《仓库资产盘点》

- **头部**：盘点基准日 2026-09-16；位置图例（🗄️仓库内 / 🖥️pet 远程 / 💽NAS）；导航表（2–9 号文档一览，各一句话）
- **§1 数据资产表**（列：资产/路径/规模/位置/状态/用途）逐项收录：
  - `datasets/cats`：552MB，8 个 zip（dataset_蒋/崔、annotation_蒋/崔 各中英文命名一份），两批双人标注，解压与清洗状态
  - `datasets/quadruped_action`：占位骨架（classes.txt + train/val/test ann list，无视频）
  - `data/papers.db`：239 篇 / paper_categories 519 条；papers 表关键字段（authors 为 JSON 数组字符串）
  - `data/extracted_papers.json`（博客 17 篇提取源）、`researched_papers.json`（frontier 调研）、`researched_papers_identity.json`（livestock/身份调研）、`papers.db.bak-seed`（8-31 种子备份）
  - `results/live/live.db`：1 stream_source / 1 screenshot
  - 💽NAS：UCF101 13320 段（登记路径，tokenizer 阶段 A 用）
  - 🖥️pet：`~/pet-action-recognition/checkpoints/*`（tsn-resnet50 等）、`~/results/batch/`（34 段原始产物）
- **§2 产物资产表**：results/ 九个子目录逐个——training（metrics.json 5 run + test_results.json + work_dirs×5 + logs/overrides）、speedrun（results.json 8-15）、batch（34 段 mp4/track.json + batch_report.md + alarm/ 3 段接触表 + 对比视频）、gate0a/0a_v2/0a_v3/0b/4（验收门视频与 track.json）、skeleton（ap10k_vis / dlc_vis）、live
- **§3 代码模块**：server 8 路由一句话表；scripts/ 27 个按用途分组（训练测试：train_model/run_test/eval_all_k400/train_all_models；推理：inference/_infer/vlm_infer/run_test_vlm；speedrun：speedrun/benchmark_speed；批处理与比较：pet_batch_run/pet_detect_track/make_followcam/pet_compare_*/pet_multi_detect/pet_seg_contact/rtmdet_cross_check/yolo11_zeroshot_audit/assert_aim_frozen/extract_keypoints_from_tracks；live：live_analyze/live_stream；工具：md_to_docx/pet_repin）；petlib 7 模块（registry/schemas/detection/tracking/keypoints/videowriter/contract_tests）；web 28 页面按 7 组；configs/ 11 文件表；models/mmaction2（vendored 只读）
- **§4 论文模块现状**：DB 统计 + 两类 research JSON 说明
- **§5 项目管理数据**：management/ 七子目录文件数（daily 3/weekly 10/monthly 3/meetings 2/team 3/projects 27/docs 9→整合后 9 篇新集）
- **§6 openspec 一览**：8 活跃表（名称/一句话定位/进度 x/y/状态/所属类别）+ 16 归档列表，详情指向 7，算法与裁决细节指向 6
- **§7 外部资产索引**：pet、NAS、third-party/ 5 库（kabr-tools/keypoint-moseq/pet-videos/PigDetect/remix-petra）
- **附录 A**：顶层散落文件清单 → 指向清理 change；**附录 B**：空/失效目录（checkpoints/ 本地空壳等）

#### 4.2 datasets.md《数据集全景》

- **§1 总览表**：名称/规模/类别数/标注情况/位置/状态（在用|占位|外部）/主要用途
- **§2 cats v1（家猫监控）**：来源（蒋/崔两批双人标注，8 zip 对应关系）、552MB、总时长约 3 小时、检测 8 类+活动标注结构、**activity 伞类占标注一半**的质量问题、与 34 段白天片段的关系
- **§3 pet_action_mammal_v0**：七类、约 3 小时、label_map 位置、用途（迁移基线；video-feature-latent 1.13 V-JEPA 微调对照）
- **§4 UCF101**：NAS 13320 段/101 类、用途（identity-action-tokenizer 阶段 A 架构验证）
- **§5 34 段白天事件片段**：**语料事实 = 短事件片段，总素材仅 14.7 分钟**（2026-09-15 修正）；批处理三率（检出 0.939/插值 0.905/校正 0.334）；3 告警段结案结论（超短片段+低在场率+红外域边缘，非算法故障）；角色定位（管线验证与演示，非训练主力）
- **§6 kinetics400**：仅作 k400 烟测的评测集
- **§7 quadruped_action 占位**：期望目录结构（引用其 README）
- **§8 标注类目规范**（detection-annotation-taxonomy **全文迁入**）：类目全集/8 类边界规则（cat/person/food_bowl/water_bowl/litter_box/toy/door_window/cat_face）/COCO 预标注映射/中期验收特征上报映射
- **§9 label_map 与 ann_file 约定**：per-model label_map、ann_file 格式（引用 `.claude/skills/datasets/`）

#### 4.3 models.md《模型》（以模型为条目：简介 + 实测结果两段式）

- **§1 我们的重要模型总览**：一张表列出实际训练/测试/使用过的全部模型（模型/类型[分类|关键点|检测]/状态[已训练|已测试|仅组件]/一句话定位）
- **§2 分类模型逐个条目**（每个固定两段式——**简介**：架构与定位一句话；**实测结果**：数字+状态+证据路径）：
  - videomaev2-base：2 个训练 run（quadruped_cats_v1，epochs=15/lr=1e-4/bs=4）均 error——结果与教训
  - slowonly-resnet50 / tsm-resnet50 / timesformer-divst：各 1 个 run 实录（metrics.json + work_dirs 路径）
  - tsn-resnet50：k400 烟测全套（top1 **0.77**/top5 **0.925**/mean1 0.6712/latency 278.8ms/RTF 0.032/显存 3068.5MB，证据 test_results.json）+ speedrun 判定示例
  - 附注：Speed Run 评测方式（run_name 批次/correct 匹配/--custom 微调模式，详见 speedrun skill）
- **§3 关键点模型条目**（同两段式）：HRNet（AP-10K）/ ResNet-101（AP-10K）/ SuperAnimal 四足——实测：MC 跟随视角 mean_conf 0.367、conf>0.5 帧仅 0.2%、四肢点 <0.25 → **2026-09-15 裁定移出管线**；对比视频在 results/skeleton/
- **§4 检测模型条目**（同两段式）：GroundingDINO（多 prompt 抽样，34 段检出率 0.939；碗全误框、camera 召回 4/1859 → 撤下裁定）/ YOLO11（zeroshot audit）/ OWLv2（对照）
- **§5 注册库其余模型速览**：26 个 registry 全表（21 分类 + 5 AVA 检测）：模型族/输入形态/checkpoint 状态/**是否已实测**（未实测者明确标注）
- **§6 结论汇总表**：按 D6 四要素一行一条

#### 4.4 training-guide.md《训练体系》

- mmaction2 机制速览（_base_ 继承、tools/train.py、vendored 快照只读原则）
- 四种训练模式（从头/预训练/加载权重/断点续训）互斥说明与选择
- registry 与触发方式（API/CLI）、四足数据集适配、configs/ 11 文件用途表、自定义 hooks
- checkpoint 管理与下载、远程执行闭环（pet 4090、`</dev/null` 后台纪律、GPU 共享）
- **历史决策回顾**（2026-07-13 计划吸收）：registry 从 DEFAULT_MODELS 抽出、19→21 族注册、数据集类别注入、四足 loader 骨架

#### 4.5 live-module.md《Live 模块》

- 落地架构：stream_sources/screenshots 表、stream_token 签名安全、视频流代理、SSE 帧级推理管线（live_analyze.py / live_stream.py：decord 读帧→滑窗 clip→同通道推送）
- 关键设计决策（吸收两篇 plan 的决策节，丢弃计划体例）：真流式也要"切"及切法对比、模型选择 UI
- PTZ 摇杆、截屏上传、演示视频端点
- 与 pet-videos 借鉴的映射（指向 8）

#### 4.6 algo-architecture.md《算法架构》（全链路算法设计说明）

- **§0 全链路架构图**（文字图，每阶段标注：输入/输出/算法/代码落点/对应 change 与决策 ID）：监控视频 → ① 宠物定位与跟踪 → ② 跟随视角生成 → ③ 动作表征学习（识别动作）→ ④ 身份识别与提取 → ⑤ 应用出口
- **§1 定位与跟踪**：GroundingDINO 开放词汇检测 + 多 prompt 抽样（每 10 帧）+ 插值平滑 + 逐帧运动校正 v5（off-alpha 0.6 等参数）；家具框与空间状态序列；**为什么**：ByteTrack 全帧率否决（D1）、GatedTracker 否决（D1b）、关键点降级辅助信号（D2）
- **§2 跟随视角生成**：follow_adaptive 裁剪（512² H.264）+ 尺寸离群过滤 + 沙发漂移渲染层过滤；作为"主表示载体"的理由
- **§3 动作表征（识别动作）**：窗口特征四候选选型（VideoMAE v1 微调 / DINOv2+帧间差分 / MammalNet / V-JEPA 2 fpc16）→ UMAP+HDBSCAN 行为簇 → 人工命名；路线 W：CatHuBERT 式行为素迭代预训练（HuBERT 伪标签 CE + <10M 小 Transformer）；**四闸门**：线性可分性/可命名率/码本健康度/身份泄漏审计；为什么零训练优先、为什么无监督发现（activity 伞类标注不可靠）
- **§4 身份识别与提取**：两条路线——① identity-action-tokenizer（FLOAT×TiTok 杂交：跨时间共享身份 tokens K_id=32 + 逐帧动作 latent z_t + 轻量解码器重建视频，重建成立则解耦成立；UCF101 阶段 A → 猫语料阶段 B）；② registry-retrieval（登记照 → DINOv2 embedding → FAISS，猫 Re-ID 与物品实例共用登记-检索抽象，D9）
- **§5 应用出口**：spot-check-cli 抽查报告（非实时抽查形态：时段→预处理→隐码→动作报告：标签/起止秒/track_id/登记身份/置信度/在场率/空间状态段，D4/D7）；behavior-anomaly-detection（正常=高频已命名簇，异常=低频簇/token 转移突变/滑窗直方图偏离，候选机制与调研前置）
- **§6 跨切面**：plf/pet_vjepa 双环境隔离（D5）、petlib 可替换模块架构（D6）、决策 ID 全局索引（D1–D9 → 各子 change design 回查表）

#### 4.7 pipeline-roadmap.md《规划与进度》（未来计划分类说明）

- **§1 未来计划四分类**（每类一张表，写明进入条件/触发条件）：
  ① **主线执行序**（当前推进）：batch-followcam-extraction（5/6 待归档）→ video-feature-latent（1/14 选型中）→ spot-check-cli（0/4）
  ② **条件启动/延后**（总管 tasks §4 登记表）：tracker-selection（多猫数据出现）、registry-retrieval（用户批准实施）、behavior-anomaly-detection（video-feature-latent 归档 + 用户发起调研）
  ③ **研究型独立立项**：identity-action-tokenizer（FLOAT×TiTok，UCF101→猫两阶段，0/9）
  ④ **已归档**：16 个 change 一行索引
- **§2 主线逐 change 说明**：目标/当前进度/验收闸门/下一步
- **§3 闸门与里程碑**：各 change 验收闸门 + 11 月中期验收 KPI
- **§4 二期计划对照**：P0 精度攻坚/P1 端侧/P2 部署验收 现状对照

#### 4.8 lessons.md《研究结论与踩坑》

- 关键点提取五大问题全文（吸收 keypoint-pitfalls）：检测器第一瓶颈/身体截断即崩溃/语义体系不统一/多动物身份切换无解/零样本不能当 GT 也不能当弱监督
- K400 经验共性：标注体系不对齐
- 复活条件分析（t13 检测/跟踪落地后）——**原文保留**
- **用户裁定时间线表**：2026-09-14 ByteTrack 全帧率版否决→抽样+插值定稿；沙发漂移渲染层过滤；2026-09-15 关键点降级辅助信号、NPZ 裁剪、运动校正 v5 参数定稿（off-alpha 0.6 / off-max-v 5% 帧宽 / 覆盖门槛 0.2，校正触发 12.0%、偏移 max 108px、锚点帧像素级一致）
- 标注表不可靠教训（activity 伞类占一半 → 无监督行为发现的原始动机）

#### 4.9 / 4.10 → 见 D5、D7

### D5 第三方借鉴文档内容规格（9 号 third-party-notes.md）

覆盖 `third-party/` 下 5 个库，但两种深度：**pet-videos、remix-petra** 两个重点项目用完整八节模板（缺一节即不合格）；**kabr-tools、keypoint-moseq、PigDetect** 三个调研型仓库用轻量条目（是什么/为何引入/是否已用上/处置建议）。

**八节模板（重点项目）**：

1. **定位与来源**：是什么、从哪来、为何留在本仓库、版本/commit pin 状态
2. **技术栈与架构速览**
3. **目录导览**：关键文件/页面/模块清单
4. **我们借鉴了什么**：具体到模块/交互/代码片段级，并**映射到本仓库落地点**（pet-videos → Live 模块源管理与播放器形态；remix-petra → 前端 UI 风格、宠物档案字段、AI 日报思路、Gemini API 现状）
5. **明确不学/反模式**（含原因）
6. **本地运行方式**：如何跑起来看效果
7. **同步策略**：vendored 只读还是可改、上游更新怎么办
8. **交叉引用**：相关 wiki 篇目/skill/change

### D6 结论与关键数据登记规范

训练/测试结论、重要数据在 3/6/7 号文档中出现时必须带**四要素**：①日期 ②来源（change 任务号或实验名）③关键数字 ④证据路径（results/… 或 data/…）。

写作时必须核对收录的已知重要数据起点（不完全清单，写入时以 json 原文为准）：
- k400 烟测全套指标（§4.3）
- 34 段批处理三率 + 3 告警段结案（§4.2/4.7）
- 语料事实修正：34 段 = 14.7 分钟（§4.2）
- 关键点 MC 实测：mean_conf 0.367 / >0.5 帧 0.2%（§4.3/4.7）
- 检测裁定：碗全误框、camera 召回 4/1859（§4.3）
- 运动校正 v5 参数与实测（触发 12.0%/偏移 max 108px/锚点像素级一致）（§4.7）
- 5 个训练 run 状态（含 error）（§4.3）

### D7 交接与协作指南（9 号）的定位与安全边界

面向**新协作者**的单一上手入口，与 1 号盘点（有什么）互补，六节结构：

1. **项目速览与当前阶段**：一句话定位 + 进度快照（活跃 change 一览、任务看板 `management/projects/*/tasks.json`、11 月中期验收 KPI）——标注快照基准日，日常进度指向任务看板
2. **环境搭建**：本地一键启动（`start_services.sh`，3000/8788）、pet/A100 连接与 conda 环境、NAS——**只写"在哪找"（引用 `.claude/skills/remote-servers/` 等），不复制凭证**
3. **工作纪律**：三阶段 OpenSpec 流程、远程只读执行/git push 同步/脚本先进仓库/禁 `/tmp` 脚本、GPU 共享——引用 AGENTS.md 与 remote-server-discipline skill
4. **协作约定**：git 提交规范（`<type>: <描述>`）、本套 9 篇 wiki 的维护责任、任务看板与报表用法
5. **FAQ**：服务起不来/连不上 pet/训练报错的排查入口（引用各主题文档）
6. **安全红线**：不提交密钥（走环境变量）、不在本地跑 GPU、不直接改远程

### D8 删除的执行顺序与回滚

整合 → 逐节核对 D3 决策表 → **删除动作单独 git commit**，绝不与新增混在一个 commit——误删可单点 revert。

## Risks / Trade-offs

- [整合走样丢细节] → D4 逐节规格即验收标准；tasks 含逐节对照核对；git 历史兜底
- [结论数字抄错] → D6 四要素 + 与 json 原文逐条核对（任务 3.3）
- [wiki 排序混乱] → id 1–10；现存无 id 文档自然排后
- [live 两篇 plan 的中间讨论被丢弃] → 只保留落地现状+关键决策，review 时可补
- [盘点/进度很快过时] → 头部标注基准日；进度日常指向任务看板
- [交接文档泄露敏感信息] → D7 安全边界：凭证只写"去哪找"

## Migration Plan

1. 按 D4–D7 规格写 10 篇新文档（id 1–10）
2. 逐节核对 D3 决策表：11 篇待删文档的信息均有落点
3. `git rm` 被吸收文档，独立 commit
4. 重写 README.md，独立 commit
5. web Wiki 页人工验证

回滚：git revert 对应 commit，无数据/代码耦合。

## Open Questions

（无——live 计划"不保留计划体例"、docx 保留原位为已定决策，异议可在 review 提出。）
