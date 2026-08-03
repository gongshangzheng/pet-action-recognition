# t10 实验笔记：DeepLabCut 零样本骨架提取——为什么不能当 GT

## 背景

任务 t10 目标是为「基于骨架的动物动作识别」探路：用 DeepLabCut Model Zoo 的 **SuperAnimal-Quadruped** 零样本模型（hrnet_w32 + FasterRCNN 检测器，39 关键点）对 pet_action_mammal_v0（2234 段哺乳动物视频，7 类动作）批量提取骨架序列，作为后续 PoseC3D 训练的输入。

## 方法

- 环境：pet 新建 conda env `dlc`（py3.11 + DeepLabCut 3.0.1 + torch 2.8.0+cu128）。
- 脚本：`scripts/extract_keypoints_dlc.py`，低层 API 逐视频推理（模型常驻、单视频失败隔离），产物 `keypoints_dlc/{train,val,test}/<stem>.npz`（39 点坐标 + 置信度 + 标签），逐视频记录 `det_rate`（有检测帧占比）与 `mean_conf`。
- 踩坑记录：torch 2.13+cu130 与 pet 驱动（12080）不兼容 → 降级；`hf_hub_download` 元数据校验失败 → 手工 curl 权重到快照目录；DLC 高层批接口被零检测视频毒化（np.stack 崩溃带崩整个 chunk）→ 改逐视频隔离。

## 全量结果（2234/2234 完成）

| split | 视频数 | det_rate ≥ 0.9 | 0.5–0.9 | 0.1–0.5 | < 0.1 | 零帧 |
|---|---|---|---|---|---|---|
| train | 1801 | 1144 | 342 | 184 | 131 | 70 |
| val | 216 | 154 | 40 | 16 | 6 | 3 |
| test | 217 | 161 | 31 | 15 | 10 | 7 |

83.8% 视频 det_rate ≥ 0.5；6.6% 基本不可用；80 段零帧。

## 结论：零样本骨架不能当 GT

人工抽检 4 段标注视频（红框 = 检测器目标框，彩点 = 39 关键点），确认了**三类系统性失败模式**，说明零样本输出连伪标签都要谨慎使用，更不具备 GT 质量：

**1. 检测器漏检——逆光/剪影/小目标直接丢失整段视频**

jump 类（猴子在树上跳跃，逆光剪影）：全程几乎无检测框，det_rate 0.04。此类视频约占 6.6%，且集中在特定拍摄条件下，直接丢弃会造成类别/场景偏置。

<video controls preload="none" src="/api/management/projects/pet-action-recognition/notes-assets/t10/jump-AIEPABQT-monkey.mp4" style="max-width:100%"></video>

**2. 多动物场景身份切换——骨架序列在时间轴上不属于同一个体**

locomotion 类（象群）：检测框在不同帧之间跳到不同大象身上。对动作识别而言，骨架序列的时序一致性是核心特征，身份一切换，序列语义就断了。我们的 social_interaction、locomotion 类大量存在多动物同框。

<video controls preload="none" src="/api/management/projects/pet-action-recognition/notes-assets/t10/locomotion-AAOYRUDX-elephants.mp4" style="max-width:100%"></video>

**3. 静物误检 + 部分遮挡——关键点落在错误目标或不完整躯体上**

social_interaction 类（水獭）：约 2 秒处检测器把白色浮球误检为动物；水下躯体不可见时 39 点只能描述头部。grooming 类（水族箱啮齿类）是质量最好的样本，关键点稳定——但即便如此也只是"可用伪标签"，单帧抖动仍明显。

<video controls preload="none" src="/api/management/projects/pet-action-recognition/notes-assets/t10/social-AHKLQIKV-otter.mp4" style="max-width:100%"></video>

<video controls preload="none" src="/api/management/projects/pet-action-recognition/notes-assets/t10/grooming-BCIMLRLL-rodent.mp4" style="max-width:100%"></video>

**根因**：SuperAnimal-Quadruped 的训练分布是实验室/纪录片的**侧视角清晰四足动物**，而我们的网络视频存在逆光、遮挡、水印、多动物、非常规视角，域差距太大。

## 后续选项（待决策）

1. **MMPose AP-10K 对照实验**（成本低）：AP-10K 在 54 种野生动物野外图像上训练，分布更接近我们的数据；同样本对比后再定。
2. **只用高质量子集**：按 det_rate ≥ 0.9 过滤（train 余 1144 段），骨架路线降级为子集验证实验，但有过滤偏置。
3. **人工标注 + 微调 DLC**（唯一可达真 GT 质量）：标 50–200 帧典型画面微调 SuperAnimal，需数小时标注投入，建议单独立项。
4. **放弃骨架路线**：RGB 已有 VideoMAEv2 Top-1 84.3%，t10 暂停并保留结论。
