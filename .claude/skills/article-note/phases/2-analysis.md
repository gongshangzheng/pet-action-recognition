# Phase 2：Analysis

## 运行策略

默认 direct；只有相对独立且耗 token 的工作才委派 subagent。可使用 assisted（1–3 个 lane）或 deep（多个 lane 并行）。不要为了凑齐 7 个模板而启动 agent。

| lane | 何时启用 | 产出 |
|---|---|---|
| background | 需要领域背景/影响 | 背景事实与来源指针 |
| methodology | 方法复杂、公式多 | 模块、机制、推导 |
| experiment | 实验数字密集 | 配置、结果、消融 |
| terminology | 术语/符号多 | 术语表、符号表 |
| citation | 需要研究脉络 | 前置工作与差异 |
| code-analysis | 有仓库且关心复现 | 代码结构与偏差 |
| image-collection | 关键图较多 | 候选图与章节映射 |

## 委派模板

```text
任务：分析 <slug> 的 <lane> 维度。
输入：.cache/article-note/<slug>/raw/ 与相关已有 analysis/。
输出：写入 .cache/article-note/<slug>/analysis/<lane>.md。
只输出：事实、来源指针（文件和行段/页面/锚点）、不确定性、待核查问题。
禁止：编造数据、复制整篇论文、创建 change、修改 management/docs/notes/。
```

互不依赖的 methodology、experiment、terminology、image-collection 可并行；code-analysis 只有仓库存在时启用。主 agent 汇总后必须回到 raw 核查冲突。

## 产出约定

每份分析至少包含：`## 结论`、`## 证据位置`、`## 不确定性与缺口`、`## 给写作的建议`。如果没有代码或图片，写明缺失，不创建虚假分析。
