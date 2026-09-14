# Tasks: pet-motion-latent-pipeline

> **依赖与执行机**：本 change 在 **pet** 上执行（plf 独立 conda 环境，与 mmaction2 的 pet 环境隔离；A100 已降级为备用算力）。**每次使用 GPU 前必须先 `nvidia-smi` 检查占用**：两卡都被占则等待或与占用者协调，禁止抢占；选空闲卡以 `CUDA_VISIBLE_DEVICES=cuda:N` 指定。
>
> **执行顺序 = 编号顺序**。§3 的用户验收是硬关卡，未通过则回退重新评估。
>
> **约定**：NPZ 关键点 schema = `keypoints (T,V,3) float16 + frame_inds + total_frames`（score 内嵌第三通道）；轨迹 JSON = `{track_id, boxes:[{frame,x1,y1,x2,y2,conf,interpolated}]}`。

## 1. petlib 接口骨架 ✅

- [x] 1.1 pet 建 plf 环境：clone pet 环境（torch 2.1.2+cu121）+ transformers==4.49.0 accelerate + setuptools<81 + numpy 钉 1.26.4；验证 pet 环境 mmcv 2.1.0 不受影响
- [x] 1.2 `petlib/schemas.py`：Detection / Track / KeypointSequence dataclass + NPZ/轨迹 JSON schema 常量
- [x] 1.3 `petlib/detection/`：Detector ABC + grounding_dino.py（transformers 懒加载）
- [x] 1.4 `petlib/tracking/`：Tracker ABC + sort_core 共享核心 + byte_track/oc_sort/bot_sort/deep_sort
- [x] 1.5 `petlib/keypoints/`：KeypointExtractor ABC + superanimal.py + vitpose_ap10k.py
- [x] 1.6 `petlib/registry.py`：create(kind, name, **cfg) 工厂（懒加载 import）
- [x] 1.7 `petlib/contract_tests.py`：契约冒烟测试——13 过（BoxMOT 真实现；BotSort/DeepOcSort 待 Re-ID 权重手动就位后参测）

## 2. 跟踪器对比选型（**延后**：单猫场景「抽样+插值」已验收足够，多猫数据出现时启用）

> BoxMOT 四候选（ByteTrack/OC-SORT/BoT-SORT/DeepSORT）已装 plf 备用；原理见 design D1c。

- [ ] 2.1 GT 制作：抽 3–5 段白天视频（含多猫），人工核对 track_id
- [ ] 2.2 固定检测源缓存 + 运行四候选
- [ ] 2.3 指标（IDF1/IDSW/碎片/平滑度）+ 选型报告
- [ ] 2.4 检测器侧误报抑制消融记录：阈值扫描已预跑——0.3→0.5 均无法抑制沙发超宽框（高置信检出），沙发漂移由渲染层尺寸离群过滤兜底（已实现于渲染脚本）

## 3. 猫居中预处理 Demo + 用户验收 ✅

- [x] 3.1 单视频 Demo：GroundingDINO 检测（39/39 帧 conf 0.95）→ 跟踪 → follow_adaptive 裁剪 → 跟随视角视频 + 对比视频 + 接触表
- [x] 3.2 第二段（074451，多动作）：发现沙发误检漂移 → 渲染层尺寸离群过滤修复（1.8×中位剔除+插值）
- [x] 3.3 ffmpeg 转 H.264（mp4v 编码 QuickTime 不支持）+ 产物回传
- [x] 3.4 **用户验收通过**：抽样+插值方案定稿（全帧率+ByteTrack 版本因抖动否决，见 design D1）

## 4. 关键点提取器对比选型（🔄 进行中）

- [x] 4.1 环境：plf 装 mmpose 1.3.2（修 numpy 2.2 连坐降级 + xtcocotools 轮子 + torch 复制 + setuptools<81）+ mim 下载 AP-10K 双候选权重（HRNet-W32 / ResNet-101）
- [x] 4.2 双候选跑两段验收视频（bbox-internal 口径）：HRNet conf 0.334/0.431，ResNet-101 conf 0.331/0.383
- [x] 4.3 crop-first 口径实测（在跟随视频上整帧识别）：conf **0.455** > bbox-internal 0.431 → **crop-first 定为管线口径**
- [ ] 4.4 **用户人工抽检**：keypoint 叠加可视化（results/gate0b/*.jpg）确认点位合理性 → 定主用提取器（HRNet vs ResNet-101 打平，抽检裁决）

## 5. 全量批处理（白天段 34/79）

- [ ] 5.1 `scripts/plf_detect_track.py`：抽样检测 + 插值平滑 → 轨迹 JSON（沿用验收方案，相机策略 follow_adaptive）
- [ ] 5.2 `scripts/make_followcam.py`：跟随视角视频（尺寸离群过滤内置）+ H.264 直写（petlib/videowriter）
- [ ] 5.3 `scripts/extract_keypoints_from_tracks.py`：crop-first 口径关键点 NPZ（§4 选型胜出者）
- [ ] 5.4 全量循环 34 段：产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 格式）
- [ ] 5.5 批处理报告：检出率/插值率/离群剔除统计；插值率 >30% 告警清单

## 6. 运动隐空间（条件启动：零训练基线不达标时才训）

> 零训练基线（B-SOiD 式）先行；「人工可命名率 ≥60% 且簇不碎」则 6.4–6.6 降级为可选增强。

- [ ] 6.1 零训练基线特征：关键点 → 手工运动学特征（速度/关节角/成对距离；窗口标准化）
- [ ] 6.2 零训练基线聚类：UMAP(30) → HDBSCAN → 行为簇
- [ ] 6.3 可命名率报告：各簇代表帧 + 人工抽 30 簇判定
- [ ] 6.4（条件）`configs/motion_latent/`：E_mot/E_id/VQ(K=512)/G；损失 = 重建 + 速度 + VQ + InfoNCE(track 级) + 平滑
- [ ] 6.5（条件）训练数据：cats + mammal_v0 + live 关键点窗口（48/24 滑窗，按源视频分组，目标 ≥15 万窗口）
- [ ] 6.6（条件）pet 空闲卡训练（≤4h，先查占用），码本利用率 ≥50%

## 7. 评测：L3 发现 + L1 探针 + 消融

- [ ] 7.1 `scripts/discover_behaviors.py`：聚类 → 代表帧 → 人工命名表
- [ ] 7.2 NMI/ARI 报告（聚类 vs 5 类人工标注）
- [ ] 7.3 `scripts/train_linear_probe.py`：线性探针 top1（判定 ≥ VideoMAEv2 基线 80%）
- [ ] 7.4 可遍历性检查：隐码插值渲染抽查
- [ ] 7.5 HQSAM 消融（可选）：mask 清洗 crop vs 原始 crop
- [ ] 7.6 摄像机策略消融：follow_adaptive（已验收）vs follow_locked vs fixed 线性探针对比

## 8. 抽查式推理 CLI

- [ ] 8.1 `scripts/spot_check_actions.py`：摄像头+时间段 → 拉录像 → 预处理 → 隐码 → 动作报告（JSON/MD：标签/起止秒/track_id/登记身份/置信度/疑似新动作/猫在场率）
- [ ] 8.2 `scripts/register_cats.py`：猫个体档案（登记照 → embedding 检索），未登记个体标「未知猫 #N」
- [ ] 8.3 端到端联调：3 个真实时段（含 1 个无猫时段）
- [ ] 8.4 L2 边界误差抽查：动作码突变 = 切换边界，±1.5s 内

## 9. 收尾

- [ ] 9.1 文档：架构图 + 脚本用法 + 双环境说明，补进 animal-action-survey §4.4 附录
- [ ] 9.2 向用户汇报：行为簇结果 + 线性探针指标
- [ ] 9.3 提交（feat: 前缀；数据资产不入库）
