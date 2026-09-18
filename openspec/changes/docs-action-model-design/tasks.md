# Tasks: docs-action-model-design

> 结构级变更：**先经用户审核 design，批准后才动正文**。

## 1. 立项与登记

- [x] 1.1 立单篇 change `docs-action-model-design`（proposal / design / tasks）
- [x] 1.2 `docs-system` 登记表：《动作识别模型设计》单篇 Change「待开」→ `docs-action-model-design`

## 2. 审核

- [ ] 2.1 用户审核 design（章节清单 / 职责 / 细章分解 / 读者动线）

## 3. 实施（审核通过后）

- [ ] 3.1 按 design 重排 《动作识别模型设计》正文：§1 总图提到顶上（合并现 §3 架构总图 + §4.6b 结构图）
- [ ] 3.2 待决策上移为 §2；框架拆为 §3 共享基座 / §4 动作提取 / §5 身份提取 / §6 潜空间与解码
- [ ] 3.3 训练 (§7) / 评测 (§8) / 谱系与合规 (§9) / 参考来源 (§10)；符号速查降为附录
- [ ] 3.4 每章补章节引言（该章在框架中的位置），内容只搬移不重写
- [ ] 3.5 引用级联：《系统架构》 / papers 笔记 / 各 change design 中「《动作识别模型设计》 §X.Y」全部重映射 + 闭合核对（悬空 0）
- [ ] 3.6 sidecar `action-model-design.json` changelog 加条 + 提交

## 4. 不做

- [ ] 4.1 设计内容的裁定（A/B/B′ 架构候选、权重选型等）→ 走 `identity-action-tokenizer` change，不在本 change
