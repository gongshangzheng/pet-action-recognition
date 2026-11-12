# Proposal: class-error-analysis

## Why

十类片段分类的测试成绩是 top-1 85.75%，但逐类差距接近 33 个百分点（`eating` 90.8% 对 `scratching` 56.4%），而项目目标同时约束「准确率 ≥75%」与「漏检率 ≤10%」两个口径。此前只有整体数字与一篇按 run 组织的训练报告，无法回答三个影响决策的问题：错误集中在哪几条类别边界上、低分类的成因是模型容量还是输入/标注、以及「activity 吞掉一切」这个说法是否成立。缺这份分析，后续的裁剪策略、补标与区间口径都会被指向错误的修复方向。

用户 2026-11-12 要求：单独出一篇逐类错误分析，图片与视频随行文推进，而不是堆在案例区。

## What Changes

- 新增逐类错误分析报告，作为「十类片段分类」主题报告中的分析章节（合并进 `management/experiments/cat-clip-training/20261112-ten-class-clips/`），覆盖：目标口径与达标状态、错误分布、运动量依赖、`grooming`/`scratching`/`drinking`/`toileting` 四个低分类、`activity` 的错误汇聚、不可评估范围。
- 新增可复用分析工具：`scripts/checks/analyze_clip_class_errors.py`（逐类指标 + Wilson 区间、错误流向、activity 吸附量、逐片段描述量、来源拆解与留一来源敏感性、案例取样、对照图、区间运动量曲线、区间整段渲染取样）与 `scripts/checks/plot_clip_class_errors.py`（分布/召回、混淆矩阵、运动量分布、三分位错误率、区间漂移五张图）。
- 新增区间整段渲染入口 `scripts/render_interval_excerpt.py`：把一条标注区间的完整跨度渲染成裁剪片、原画与 12 帧拼图，用于判断错判是模型分不清还是窗口取样取错位置。
- 报告正文的图片与视频改为行内引用（`assets/<sha>.png`、`media/<sha>.mp4`），页面按报告目录改写路径并内嵌播放；结构化案例区不再重复铺已内联的素材。

## Capabilities

### New Capabilities

- `class-error-analysis`：逐类错误分析的证据要求与报告口径（新增）。

### Modified Capabilities

（无）

## Impact

- 报告：`management/experiments/cat-clip-training/20261112-ten-class-clips/`（正文新增 10 个三级小节，案例素材 35 件）。
- 代码：`scripts/checks/analyze_clip_class_errors.py`、`scripts/checks/plot_clip_class_errors.py`、`scripts/render_interval_excerpt.py` 新增；`web/src/components/common/MarkdownRenderer.vue`、`web/src/views/management/ExperimentsPage.vue`、`web/src/api/experiments.js`、`server/parsers/experiments_parser.py` 支持正文内嵌媒体。
- 文档：`AGENTS.md` 的当前基线补入逐类发现与待办；documentation skill 的标题规则同步到上下游仓库。
- 数据：只在 `results/`（不入库）与本机临时目录产生中间产物，未改动数据集与源标注。
