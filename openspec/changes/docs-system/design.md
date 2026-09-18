# Design: docs-system

## 文档登记表（唯一权威）

| 编号 | slug | 标题 | 职责边界（只管什么） | 单篇 Change |
|---|---|---|---|---|
| 1 | repo-inventory | 仓库资产盘点 | 资产索引 + 归档 change 清单 | — |
| 2 | datasets | 数据集全景 | 数据集 / 语料 / 标注形态 | — |
| 3 | models | 模型 | 模型资产 | — |
| 4 | training-guide | 训练体系 | mmaction2 训练 | — |
| 6 | **architecture** | **系统架构** | **结构 / 设计 / 决策的唯一入口**（跨模型视角） | `docs-architecture` |
| 7 | identity-and-retrieval | 身份标识与检索 | 定位追踪 / Re-ID / 物体标识原理 | — |
| 8 | identity-tokenizer | 身份-动作 Tokenizer | **单模型内部设计**（聚合粒度 / 离散化 / 对称架构归此） | 待开 |
| 9 | lessons | 研究结论与踩坑 | 实验教训 | — |
| 10 | third-party-notes | 第三方项目借鉴 | 外部仓库笔记 | — |
| 11 | handover-guide | 交接与协作指南 | 交接 | — |
| 5 | live-module | Live 模块 | 实时视频流 | — |
| — | papers/docs/* | 研究笔记 | 论文调研 / 综述（不在 wiki 编号体系内） | — |

**职责裁定（2026-09-17）**：跨模型的内容归 6 号架构；单模型内部设计归 8 号 Tokenizer。
例：实时 / 流式（涉及门控 + 分段 + 判别多模型协作）→ 6 号；λ 聚合粒度 / 离散化 / 对称架构 → 8 号。

## 跨文档引用规范

- 格式：`[N 号《标题》](./<slug>.md)`；带节号时 `[N 号 §X.Y](./<slug>.md)`
- **引用必须闭合**：指向的标题必须真实存在；编号重映射后全仓核对
- 正文中引用决策用「名字（Cxx）」，不裸用编号

## 文档系统功能范围（渲染层 / 前端）

| 功能 | 说明 | 涉及 |
|---|---|---|
| TOC 强调符号处理 | 章节列表对标题中的 `**` 丢弃（或渲染为强调），不显示符号字符 | `web/src/utils/markdown.js`（extractToc / slugify）|
| **sidecar json** | 每篇 `management/docs/<slug>.md` 配同名 `<slug>.json`：`changelog`（演进：日期 + 一句话 + commit）/ `progress`（进度）/ `appendix`（附录设计说明，markdown 字符串）/ `related`（相关文档：title + slug + desc）| `server/routers/management.py`（get_doc_detail 读取同名 json 一并返回）|
| 渲染布局 | **顶部按钮**：演进记录、进度（点击弹层）；**底部独立块**：相关文档、附录；无字段不渲染空块 | `DocPage.vue` + 弹层 / 底部块组件 |

## 与其他路线的关系

- 管线类 change（2.x / 4x）登记在 `pet-motion-latent-pipeline` 路线图，**不在**本 Change
- 文档类 change 登记在本 Change 的 tasks
