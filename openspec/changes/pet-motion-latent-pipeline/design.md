# Design: pet-motion-latent-pipeline

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
- 跟踪：**对比选型实验**，候选 ByteTrack / OC-SORT / BoT-SORT / DeepSORT。PigTrack 畜牧基准（`2507.16639`）显示 SORT 系在检测指标上占优，但那是猪圈域——须在本域验证。实验设计：固定同一检测源（GroundingDINO 白天检出），对 3–5 段人工核对过 track_id 的视频小样本 GT，比 IDF1 / IDSW / 轨迹碎片数 / 框平滑度；判定标准（IDF1 优先，碎片与抖动为辅）与结论一并记录。输出 = 平滑轨迹（滑动平均窗口 5 帧）+ track_id + 插值标记
- 居中裁剪：虚拟摄像机——裁剪窗口位置/尺寸沿轨迹线性渐变（窗口渐变速率上限防跳切），外扩 1.2×；输出 768×768
- 跟踪的四个作用（身份连续/漏检补全/平滑/检测节流）写入 spec 的原因：它们是可验收行为，不是实现细节

### D2: 关键点提取器可插拔——SuperAnimal vs ViTPose 双候选对比（不做先验断言）

两个候选各有依据，**无实验前不预设胜负**：
- SuperAnimal-Quadruped（DeepLabCut 生态，26 点四足专用定义，零样本）
- ViTPose+（AP-10K 动物数据训练变体，AnimalFormer 在羊上验证过）

关卡 0 = 双候选对比实验：同 5 段白天抽帧跑两套，比①置信度分布 ②关键点时序抖动（相邻帧位移方差）③可视化人工抽检 ④各自关键点训隐空间后的 5 类线性探针 top1。决策标准：探针 top1 为主、抖动与抽检为辅；平手则取 SuperAnimal（DLC 生态与现有脚本兼容）。接口做成可插拔（统一输出 NPZ schema），落选者保留为备选。

### D2b: HQSAM 的定位——显式消融实验，不是默默砍掉

mask 在「关键点隐空间」主链上不被消费，因此不进主链；但「mask 清洗背景后的 crop」可能缓解白天背景捷径学习——这是一个待验证假设，不是可以忽略的工程细节。故列 3.5 消融任务：mask-cleaned crop vs 原始 crop 各训线性探针对比。HQSAM 另一个保留用途：体型/毛色分析（二期）。

### D3: 隐空间架构（FLOAT/Keypoint-MoSeq 杂交，数字人工具 + 行为学目标）

```
x (48,34) ─E_mot(1D CNN+Transformer)─► h(12,256) ─VQ(K=512,d=32)─► z(12,32) ─G─► x̂
x ─E_id(池化+MLP)─► s(64)
L = L1(x,x̂) + 1.0·L1(Δx,Δx̂) + L_vq + 0.1·InfoNCE(s) + 0.01·‖Δz‖²
```
- VQ 码本 K=512：离散 token 是 L3 聚类/直方图的基础；码本利用率 <50% 触发重置（防塌缩）
- 身份码对比学习：监督信号 = 源视频 ID（免费）
- 窗口 48 帧 stride 24；参数量目标 <10M；单卡 4090 训练 ≤4h
- 与 Keypoint-MoSeq 的差异：HMM → VQ-VAE/Transformer；实验室小鼠 → 家庭宠物监控；且产出离散 token 便于 L2 切分与统计

### D4: 抽查式推理为独立 CLI，非 live 模块扩展

用户确认生产形态 = 非实时抽查。CLI `scripts/spot_check_actions.py --camera C --from T --to T`：拉取该时段录像 → 复用预处理管线 → 隐码 → 动作报告（JSON/Markdown）。live 模块零改动。

### D5: 环境隔离

GroundingDINO/HQSAM/ViTPose 依赖重且与 mmaction2 的 mmcv 约束冲突风险高 → pet 上新建 conda env `plf`（precision livestock farming），管线脚本以 subprocess + env 切换调用，产物落盘交接（NPZ/pkl），不跨环境 import。

## Risks / Trade-offs

- [白天段 SuperAnimal 关键点质量未验证（低风险）] → 管线第 0 关卡保留：抽 5 段白天可视化抽查
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
