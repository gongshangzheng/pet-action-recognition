# Tasks: docs-action-model-design

> 结构级变更：**先经用户审核 design，批准后才动正文**。

## 1. 立项与登记

- [x] 1.1 立单篇 change `docs-action-model-design`（proposal / design / tasks）
- [x] 1.2 `docs-system` 登记表：本文档单篇 Change「待开」→ `docs-action-model-design`
- [x] 1.3 文档改名：《身份-动作 Tokenizer：动作识别模型设计》→《动作识别模型设计》，slug → `action-model-design`；全仓取消「N 号」指代
- [x] 1.4 design 记录两方案（单模型 / 双模型）对结构的影响

## 2. 审核

- [ ] 2.1 用户审核 design（目标结构 / 章节清单 / 细章分解 / 读者动线）

## 3. 实施（审核通过后）

- [ ] 3.1 §1 框架总图提到顶上：完整结构图（两方案 + 下游：行为素序列 → 分段 → 动作识别）+ 模块地图
- [ ] 3.2 [ ] §2 待决策上移（模型级 🔴 2 + 🟡 8 表）
- [ ] 3.3 §3 方案一（单模型 TIV+TV）/ §4 方案二（双模型外挂身份 + 动作编码器）各自成章
- [ ] 3.4 §5 共有机制（正交约束 / 聚合粒度 / patchify 或逐帧 2D / 变长 / 解码与重建 proxy）
- [ ] 3.5 §6 训练与对比实验 / §7 评测矩阵 / §8 下游：行为素序列 → 动作识别 / §9 谱系与合规 / §10 参考来源；符号速查降为附录
- [ ] 3.6 每章补章节引言（该章在框架中的位置），内容只搬移不重写
- [ ] 3.7 引用级联：《系统架构》/ papers 笔记 / 各 change design 中指向本文档的节引用全部重映射 + 闭合核对（悬空 0）
- [ ] 3.8 sidecar `action-model-design.json` changelog 加条 + 提交

## 4. 不做

- [ ] 4.1 设计内容的裁定（T-A3b2 patchify 取舍、T-A5d 两方案开口项、权重选型等）→ 走 `identity-action-tokenizer` change，不在本 change
