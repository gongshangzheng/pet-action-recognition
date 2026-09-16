# Tasks: docs-repo-inventory

## 1. 资产盘点（1 号文档素材定稿）

- [ ] 1.1 复核数据资产数字：datasets/cats 规模与两批标注、quadruped_action ann list 行数、papers.db（239 篇/519 类目）、NAS UCF101 路径
- [ ] 1.2 复核产物数字：results/training（metrics/test_results 关键指标）、speedrun/results.json 日期、batch 34 段与告警 3 段、gate0a/0b/4、skeleton、live.db
- [ ] 1.3 整理 scripts/ 27 个脚本按用途分组清单（推理/训练/批处理/关键点/其他）与顶层散落文件清单

## 2. 撰写 7 篇统一文档（management/docs/，id 1–7，frontmatter 齐全）

- [ ] 2.1 repo-inventory.md（id:1 仓库资产盘点）：按 design D4 六类资产 + 三级位置标注 + 待清理项附录 + 指向 2–7 的索引，头部标注盘点基准日 2026-09-16
- [ ] 2.2 training-guide.md（id:2）：吸收 mmaction2-overview + model-onboarding 全部有效内容 + 2026-07-13 计划的落地决策回顾
- [ ] 2.3 data-and-annotation.md（id:3）：吸收 detection-annotation-taxonomy + 数据集现状（cats/ quadruped / NAS）
- [ ] 2.4 live-module.md（id:4）：整合两篇 live plan 的落地现状与关键设计决策（不保留计划体例）
- [ ] 2.5 research-notes.md（id:5）：吸收 keypoint-extraction-pitfalls 全部结论与复活条件分析
- [ ] 2.6 third-party-notes.md（id:6）：合并两篇第三方借鉴文档，保留"可借鉴/反模式"
- [ ] 2.7 research-roadmap.md（id:7）：吸收 2026-08-15 二期计划（KPI+路线+现状对照）+ openspec 8 活跃/16 归档 change 索引

## 3. 信息保全核对（删除前置闸门）

- [ ] 3.1 按 design D3 决策表逐篇对照：11 篇待删文档的结论/数据/决策/路径/命令在新文档均有落点，核对结果记录到本 change（notes 追加或 PR 描述）
- [ ] 3.2 确认 tasks.md（wiki）无 tasks.json 之外的有价值信息；有则补入 7 号文档后再删

## 4. 删除与重写（独立 commit，可单点回滚）

- [ ] 4.1 `git rm` 8 篇被吸收 wiki + tasks.md（commit：`docs: remove wiki docs absorbed into unified set`）
- [ ] 4.2 `git rm` docs/plans/ 两篇计划（commit：`docs: remove landed plans absorbed into wiki`）
- [ ] 4.3 重写根 README.md：8 大模块总览 + 指向 repo-inventory（commit：`docs: rewrite README module overview`）

## 5. 验证

- [ ] 5.1 打开 web（localhost:3000）Wiki 页：7 篇按 id 1–7 排序、旧文档消失、frontmatter 标题/摘要正确
- [ ] 5.2 全库文档清点：docs/ 仅剩 docx；management/docs/ = 7 篇新文档；`git log` 三个 commit 独立可 revert
- [ ] 5.3 提交剩余 change 目录更新（tasks 勾选）并收尾汇报
