# Design: multi-object-detect-gate

> 继承总管 `pet-motion-latent-pipeline` design.md 的 D1（工程形态）、D9（登记-检索架构）。本文件只记本子 change 的增量决策。

## Decisions

### MD1: 多 prompt 一次前向，不多跑

GroundingDINO 开放词汇天然支持点号分隔多 prompt（`cat. bed. table. sofa. shelf.`），一次前向返回全部类别的框。成本与单 prompt 相同。

### MD2: 五类清单的取舍（2026-09-14 用户裁定）

- **保留**：cat / bed / table / sofa / shelf（v1 版验收效果不错）
- **撤下**：bowl（文本检测偏掉，实测 2952 次检出全是误框）、camera（召回 4/1859）
- 静态小物体后续走总管 D9：SAM 一次分割 + 固定机位缓存 + 定期重分割 + 登记照检索

### MD3: 空间状态判定规则

- 判定依据 = 猫框**底边中点**（脚部位置）是否落入家具框内——防透视假象（猫在家具后面时框会重叠但脚不在框内）
- 迟滞：状态切换需持续 ≥1.5s 才生效，防单帧抖动闪变
- 默认值 `on floor`；无猫检出时状态保持前值
