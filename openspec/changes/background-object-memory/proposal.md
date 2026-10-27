# Proposal: background-object-memory

> 总管旁支（架构 §4 环节①「背景对象层」）。**状态：立项，待实施批准**。
> 机制稿件来源：架构 §4「背景对象层」+ `registry-retrieval` design R1/R2/R2b（2026-09-14 讨论稿，本次迁入）。

## Why

现有检测层只能回答「猫在哪」，回答不了「画面里本来有什么、现在还在不在」：

1. **GroundingDINO 只检出写了 prompt 的类别**（现为 `cat/bed/table/sofa/shelf`）——无 prompt 的物体（猫碗、饮水机、猫爬架、纸箱）检不到。
2. **被猫遮挡的物体会消失**：猫趴在碗上、挡在门前时 GDINO 检不到框；下游的空间关系状态层（`cat on {家具}`）就会在此期间断档。
3. **跟随视角下背景持续变化**：相机随猫移动 → 画面内背景物件不断进出；没有一层「背景里有什么、在哪」的持续记忆，空间上下文就只是逐帧检测的快照，无法支撑「这段时间一直在沙发上」这类判断。
4. **静态物体不需要逐帧检测**：固定机位下碗/家具几乎不动，逐帧跑检测纯属浪费；真正需要高频的只有猫。

已有反面证据：GroundingDINO 文本检测「碗」实测全误框、「camera」召回 4/1859（`multi-object-detect-gate` 已裁定撤下这两类）——**静态物体实例识别不能靠文本 prompt**，必须走「一次分割 + 长期记忆 + 变更触发」。

## What Changes

- 新增**背景对象记忆层**（每个摄像头一份）：关键帧上 SAM 分割 → 场景常驻物体清单
  `{object_id, mask_rle, bbox, embedding, first_seen, last_moved, semantic_label}`，per-camera JSON/NPZ 持久化（gitignore）。
- **关键帧触发**（不是逐帧）：区域变化超阈值（裁剪窗口移动 / 相机真实转动）或距上次分割超时 → 关键帧上跑 SAM。
- **变更检测三重过滤**（修正「猫一动就误触发」）：① 前景减去膨胀后的猫框 ② 非猫变动需持续 ≥X 秒（初值 10s）③ 只对变动邻域（bbox 外扩 20%）局部重分割。
- **两次关键帧之间的免费换算**：真实机位不动 → 物体在原帧坐标系静止 → 裁剪帧内位置 = 全局坐标 − 裁剪偏移，无需重新分割。
- **三项职责**：① 背景对象记忆（含被遮挡期间）② 纠正 GroundingDINO 错检 ③ 补它的盲区（无 prompt 物体）。
- 与 `L3` 抠像解耦：本层分割**背景物体**（SAM，关键帧），`pet-background-removal` 抠**猫**（rembg 小模型，逐帧）——两个用途、两套模型。

## Capabilities

### New Capabilities

- `background-object-memory`: 场景常驻物体清单的建立、维护与变更触发的局部重分割契约，以及对检测层输出的纠正/补全职责。

## Impact

- 新增 `petlib/background/`（清单存储 + 触发状态机）与关键帧分割 CLI（SAM 权重在 pet）。
- 消费方：`batch-followcam-extraction`（已归档）的空间状态层、`registry-retrieval`（物品实例识别共用登记-检索）。
- 产物 per-camera 清单文件（gitignore），不动原视频与既有轨迹 JSON。
- 四项实验测定项（阈值/选型/过滤/合并）在实施时定值，本 change 只定契约与机制。

## 不做

- 不做逐帧背景分割；不做实时在线服务。
- 不承担猫本体抠像（归 `pet-background-removal`）。
- 不解决物品**语义类别**的开放词表识别（那是 `registry-retrieval` 的登记-检索）。
