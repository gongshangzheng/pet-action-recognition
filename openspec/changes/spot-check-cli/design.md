# Design: spot-check-cli

> 继承总管 D5/D6；登记-检索架构见 `registry-retrieval` D9。**总管 D4/D7/A7 已物理迁入本文件（ID 不变）**。

## Decisions

### C1: CLI 形态

`scripts/spot_check_actions.py --camera C --from T --to T`：拉录像 → 复用预处理管线（multi prompt 检测 + 运动校正 + 跟随裁剪）→ 隐码（video-feature-latent 选型胜出编码器 + 簇映射）→ 动作报告（JSON/Markdown）。分钟级延迟可接受。

### C2: 身份登记

登记照（每猫 3–5 张清晰 crop）→ DINOv2 embedding → FAISS；新 crop 最近邻检索；未登记个体标「未知猫 #N」。与物品识别共用 `petlib/identity/` 抽象（总管 D9）。


---

## 自总管迁入的决策（ID 不变，交叉引用保持有效）

### D4: 抽查式推理为独立 CLI，非 live 模块扩展

用户确认生产形态 = 非实时抽查。CLI `scripts/spot_check_actions.py --camera C --from T --to T`：拉取该时段录像 → 复用预处理管线 → 隐码 → 动作报告（JSON/Markdown）。live 模块零改动。

### D7: 身份体系——"这是哪只猫"的三层答案

| 层 | 时间范围 | 负责者 | 原理 |
|---|---|---|---|
| 帧内 | 单帧 | 检测器（GroundingDINO/YOLO11） | 检出几只猫、各在什么位置 |
| 轨迹内（秒~分钟） | 连续段 | 跟踪器 track_id（ByteTrack 等） | 外观+运动关联，保证序列内是同一只；无学习 |
| 跨段/跨天（真·识别） | 永久 | **猫个体档案 + 检索式 Re-ID** | 登记照（每猫 3–5 张清晰图）→ 特征（DINOv2/SuperAnimal 外观特征）→ 度量学习 embedding → 新 crop 最近邻检索 |

**借鉴来源（畜牧已验证）**：BMCTrack-d（`2609.03463`，猪背花纹 Re-ID——猫花纹更独特，天然适配）；Label a Herd in Minutes（`2204.10905`，自监督+度量学习+主动学习，10 分钟标注全场）；AutoCattloger（`2508.15945`，登记档案+流式检索）；ReCowGnition（`2607.22071`，封闭群脸识别基准）。

**关键洞察**：家庭是**极端 closed-set**（2–5 只，远小于牧场几十头）——识别是"小规模检索"而非开放集分类，登记照+最近邻已足够；z_id（隐空间身份码）只作与视觉 Re-ID 融合互验的辅助信号，不作主依据（其判别性无保证，见 D3）。


---

## 附录：算法原理（自总管附录 A 迁入）

### A7 推理头

**线性探针（L1 评测）**
- 是什么：冻结特征提取器，只训练最后一层线性分类器
- 为什么：衡量表征质量的标准方法——如果隐空间线性可分到 5 类动作，说明表征真的编码了动作语义；参数量小，小数据不易过拟合

**DINOv2（猫个体识别特征，9.2）**
- 是什么：自监督 ViT 特征（1.42 亿图训练），通用视觉表征
- 为什么：猫个体识别用其特征 + 度量学习/最近邻（借鉴 Label a Herd in Minutes 的自监督配方），避免训练专用 Re-ID 网络
