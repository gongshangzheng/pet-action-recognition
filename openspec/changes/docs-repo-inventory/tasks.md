# Tasks: docs-repo-inventory

## 1. 素材取证（写文档前的事实核对）

- [x] 1.1 数据资产取证：datasets/cats 8 个 zip 清单与大小、quadruped_action ann list 行数、papers.db（239 篇/519 类目）、extracted/researched JSON 内容抽样、NAS UCF101 路径、pet 远程已知路径（checkpoints、~/results/batch）
- [x] 1.2 产物取证：results/ 逐子目录记录路径+生成日期+关键数字——training（metrics.json 5 run 全部 error、test_results.json k400 指标）、speedrun（results.json 366 条 24 模型）、batch（batch_report.md 三率+3 告警结案）、gate0a/0a_v2/0a_v3/0b/4、skeleton、live.db
- [x] 1.3 代码取证：scripts/ 26 个逐个一句话用途、server 7 路由、petlib 4 模块、web 28 页面分组、configs/ 14 文件用途（含 hooks/aim_modules 子目录）
- [x] 1.4 管线与身份取证：精读 openspec 总管（design D1–D9 裁决与决策索引、tasks §2 主线序/§4 延后旁支登记）+ 7 个子 change（任务/闸门/状态）；产出「结论与关键数字清单」（D6 四要素）+「算法阶段素材清单」（每阶段算法/输入输出/否决方案及理由）+**「身份一致性原理表」**（同猫跨时间/视角特征相似、不同猫区分——从 Re-ID、FAISS 检索、track 级 InfoNCE 抽取证据），供 2.3/2.6/2.7/2.8/2.9 使用

## 2. 撰写 11 篇统一文档（management/docs/，id 1–11，frontmatter 齐全；逐节按 design D4 对应规格写）

- [ ] 2.1 repo-inventory.md（D4.1）：头部基准日+位置图例+导航表；§1 数据资产表、§2 产物资产表、§3 代码模块、§4 论文、§5 管理数据、§6 openspec 一览、§7 外部资产、附录 A 散落文件/B 空目录
- [ ] 2.2 datasets.md（D4.2）：§1 总览表、§2–7 六个数据集逐个（含 14.7 分钟语料事实、activity 伞类问题）、§8 标注规范全文迁入、§9 label_map/ann_file 约定
- [ ] 2.3 models.md（D4.3）：重要模型逐个条目（两段式：简介 + 实测结果）——分类 5 个（含 5 run 与 k400 烟测全套指标）、关键点 3 个（裁剪裁定）、检测 3 个（撤下裁定）、§5 registry 全表标注未实测项、§6 结论汇总（D6 四要素）
- [ ] 2.4 training-guide.md（D4.4）：机制/四模式/registry/configs 表/checkpoint/远程闭环 + 2026-07-13 计划历史决策回顾
- [ ] 2.5 live-module.md（D4.5）：落地架构（表结构/stream_token/SSE 管线）+ 关键决策（不保留计划体例）
- [ ] 2.6 architecture.md（D4.6）：§0 术语表（含对比学习定义）、§1 完整结构总览表、§2–5 五阶段详解（含身份一致性原理与对比学习视角）、§6 应用出口、§7 跨切面、§8 进度与未来计划四分类 + 闸门里程碑 + 二期对照
- [ ] 2.7 identity-and-retrieval.md（D4.7 整合专篇）：§0 三层概览、§1 定位追踪、§2 跟随视角、§3 猫 Re-ID（含对比学习视角：同猫跨时间/视角共享身份）、§4 RAG 式物体实例标识（含对比学习视角）、§5 统一登记-检索抽象、§6 数据资产、§7 未决与依赖
- [ ] 2.8 identity-tokenizer.md（D4.8 专篇）：§1 问题与定位、§2 FLOAT×TiTok 架构三要点（身份 tokens 跨时间共享即 positive invariance 写进架构）、§3 两阶段路线（stage B track 级 InfoNCE 对比损失）、§4 评测矩阵（身份检索/泄漏/交换重建）、§5 训练配方、§6 验收裁定与回流、§7 环境依赖
- [ ] 2.9 lessons.md（D4.9）：关键点五大问题全文、K400 共性、复活条件原文、用户裁定时间线表（含运动校正 v5 参数）
- [ ] 2.10 third-party-notes.md（D5）：两项目各八节模板（定位来源/技术栈/目录导览/借鉴点→本仓库落地映射/反模式/运行方式/同步策略/交叉引用）
- [ ] 2.11 handover-guide.md（D7）：六节（速览快照/环境搭建/工作纪律/协作约定/FAQ/安全红线），凭证只写"去哪找"不写值

## 3. 信息保全核对（删除前置闸门）

- [ ] 3.1 按 D3 决策表逐篇对照：11 篇待删文档的结论/数据/决策/路径/命令在新文档均有落点，核对结果记录在本 change
- [ ] 3.2 确认 wiki tasks.md 无 tasks.json 之外的有价值信息；有则补入 6 号文档后再删
- [ ] 3.3 D6 已知重要数据清单逐条核对：新文档中的数字与 json/md 原文一致（k400 指标、三率、14.7 分钟、0.367、4/1859、v5 参数、5 run 状态）
- [ ] 3.4 架构与专篇与 change 原文一致性抽查：五阶段算法描述、否决理由、决策 ID 引用与各 design 原文一致；进度四分类与总管 tasks §2/§4 登记一致；tokenizer 专篇七节与 identity-action-tokenizer change 一致；**identity-and-retrieval 与 change 原文一致**

## 4. 删除与重写（独立 commit，可单点回滚）

- [ ] 4.1 `git rm` 8 篇被吸收 wiki + tasks.md（commit：`docs: remove wiki docs absorbed into unified set`）
- [ ] 4.2 `git rm` docs/plans/ 两篇计划（commit：`docs: remove landed plans absorbed into wiki`）
- [ ] 4.3 重写根 README.md：8 大模块总览 + 指向 repo-inventory（commit：`docs: rewrite README module overview`）

## 5. 验证

- [ ] 5.1 打开 web（localhost:3000）Wiki 页：11 篇按 id 1–11 排序、旧文档消失、frontmatter 标题/摘要正确
- [ ] 5.2 全库文档清点：docs/ 仅剩 docx；management/docs/ = 11 篇新文档；`git log` 删除/重写 commit 独立可 revert
- [ ] 5.3 以新人视角走查 handover-guide：引用的每条路径/脚本/skill 均存在，全文无明文凭证
- [ ] 5.4 提交 change 目录更新（tasks 勾选）并收尾汇报
