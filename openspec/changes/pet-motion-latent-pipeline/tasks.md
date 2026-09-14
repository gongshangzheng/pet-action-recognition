# Tasks: pet-motion-latent-pipeline

> **依赖与执行机**：本 change 在 **pet** 上执行（plf 独立 conda 环境，与 mmaction2 的 pet 环境隔离；A100 已降级为备用算力）。**每次使用 GPU 前必须先 `nvidia-smi` 检查占用**：两卡都被占则等待或与占用者协调，禁止抢占；选空闲卡以 `CUDA_VISIBLE_DEVICES=cuda:N` 指定。
>
> **执行顺序 = 编号顺序，严格顺序执行**（用户要求 2026-09-14）：当前任务未完成/未验收前，不得跳过做后面的节。用户验收节点：§4.5、§6.4。
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

## 2. 猫居中预处理 Demo + 用户验收 ✅

- [x] 2.1 单视频 Demo：GroundingDINO 检测（39/39 帧 conf 0.95）→ 跟踪 → follow_adaptive 裁剪 → 跟随视角视频 + 对比视频 + 接触表
- [x] 2.2 第二段（074451，多动作）：发现沙发误检漂移 → 渲染层尺寸离群过滤修复（1.8×中位剔除+插值）
- [x] 2.3 ffmpeg 转 H.264（mp4v 编码 QuickTime 不支持）+ 产物回传
- [x] 2.4 **用户验收通过**：抽样+插值方案定稿（全帧率+ByteTrack 版本因抖动否决，见 design D1）

## 3. 关键点提取器对比选型 ✅（裁定：降级为辅助信号）

- [x] 3.1 环境：plf 装 mmpose 1.3.2（修 numpy 2.2 连坐降级 + xtcocotools 轮子 + torch 复制 + setuptools<81）+ mim 下载 AP-10K 双候选权重（HRNet-W32 / ResNet-101）
- [x] 3.2 双候选跑两段验收视频（bbox-internal 口径）：HRNet conf 0.334/0.431，ResNet-101 conf 0.331/0.383
- [x] 3.3 crop-first 口径实测（在跟随视频上整帧识别）：conf **0.455** > bbox-internal 0.431 → **crop-first 定为管线口径**
- [x] 3.4 **用户人工抽检完成（2026-09-14）**：骨架连线视频交付后用户判定「关键点连出但提取不出信息」→ **裁定：关键点降级为辅助信号**（在场率/运动强度/簇命名参考），主表示切换预训练视频编码器特征（design D8）

## 4. 多目标检测 + 空间关系状态验证（⬅️ 当前任务，用户验收节点）

- [ ] 4.1 **多 prompt 同帧检测**：GroundingDINO `"cat. bed. table. sofa. shelf. bowl. camera."`（清单可调）一次前向多类打框；验收 = 各类物体框均正确（逐类着色+标签的可视化视频）。**正式脚本 = `scripts/plf_multi_detect.py`**（入版本管理；产物 = `<out>/multi_detect.mp4` + `multi_detect.json` 检出统计；禁止放 /tmp）
- [ ] 4.2 **空间关系状态层（规则，无学习）**：猫框**底边中点**（脚部位置）落入家具框内 → 状态 = `"cat on bed/table/shelf/sofa"`，否则 `"on floor"`；切换要求**持续 ≥1.5s**（迟滞防抖）；防透视假象 = 底边点判定而非框 IoU
- [ ] 4.3 **验收视频叠加状态文字**（如 `cat on bed`），**用户抽检通过**后：§5 批处理检测环节改用多 prompt，家具框 + 空间状态作为场景上下文辅助信号（同时语义化解决沙发误检：猫框落入沙发框时做一致性校验）

## 5. 全量批处理（白天段 34/79）

- [ ] 5.1 `scripts/plf_detect_track.py`：多 prompt 抽样检测 + 插值平滑 → 轨迹 JSON（沿用验收方案，相机策略 follow_adaptive）；家具框一并落盘
- [ ] 5.2 `scripts/make_followcam.py`：跟随视角视频（尺寸离群过滤内置）+ H.264 直写（petlib/videowriter）
- [ ] 5.3 `scripts/extract_keypoints_from_tracks.py`：crop-first 口径关键点 NPZ（HRNet-W32-AP10K；**辅助信号用途**：在场率/运动强度/消融对照）
- [ ] 5.4 全量循环 34 段：产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 格式）
- [ ] 5.5 批处理报告：检出率/插值率/离群剔除统计；插值率 >30% 告警清单

## 6. 运动隐空间表征（视频特征主链，零训练；自训版条件启动）

> 关卡 0B 裁定后修订：主表示 = 预训练编码器零训练特征（design D8）；自监督 VQ 训练仅在零训练基线不达标时启动。

- [ ] 6.1 主表示选型实验：VideoMAEv2 vs DINOv2 在两段验收跟随视频 + 抽 3 段白天段上各出窗口特征（16 帧窗口 stride 8）→ UMAP 可视化 + 时序连续性（相邻窗口余弦距离）→ 人工看簇代表帧可命名性；判定：可命名簇比例为主，打平取 VideoMAEv2
- [ ] 6.2 胜出编码器接入 petlib（`petlib/features/` 抽象 + 契约测试复用）
- [ ] 6.3 全量窗口特征提取 + UMAP(30) → HDBSCAN → 行为簇
- [ ] 6.4 可命名率报告：各簇代表帧（叠加关键点辅助参考）+ 人工抽 30 簇判定（**用户验收节点**）
- [ ] 6.5（条件）`configs/motion_latent/`：自训 VQ 版——输入修订为视频特征序列 (48,768)，其余架构不变（E_mot/E_id/VQ(K=512)/G；损失 = 重建 + 速度 + VQ + InfoNCE(track 级) + 平滑）
- [ ] 6.6（条件）训练数据：cats + mammal_v0 + live 窗口（按源视频分组，目标 ≥15 万窗口）；pet 空闲卡训练（≤4h，先查占用），码本利用率 ≥50%

## 7. 评测：L3 发现 + L1 探针 + 消融

- [ ] 7.1 `scripts/discover_behaviors.py`：聚类 → 代表帧 → 人工命名表
- [ ] 7.2 NMI/ARI 报告（聚类 vs 5 类人工标注）
- [ ] 7.3 `scripts/train_linear_probe.py`：线性探针 top1——主对照 = **同一编码器在原始整帧视频上的特征**（检验跟随预处理增益）；参考 = VideoMAEv2 全量微调基线
- [ ] 7.4 可遍历性检查：隐码插值渲染抽查（可选学习版启动时）
- [ ] 7.5 HQSAM 消融（可选）：mask 清洗 crop vs 原始 crop
- [ ] 7.6 摄像机策略消融：follow_adaptive（已验收）vs follow_locked vs fixed 线性探针对比

## 8. 抽查式推理 CLI

- [ ] 8.1 `scripts/spot_check_actions.py`：摄像头+时间段 → 拉录像 → 预处理 → 隐码 → 动作报告（JSON/MD：标签/起止秒/track_id/登记身份/置信度/疑似新动作/猫在场率/**空间状态段**）
- [ ] 8.2 `scripts/register_cats.py`：猫个体档案（登记照 → embedding 检索），未登记个体标「未知猫 #N」
- [ ] 8.3 端到端联调：3 个真实时段（含 1 个无猫时段）
- [ ] 8.4 L2 边界误差抽查：动作码突变 = 切换边界，±1.5s 内

## 9. 收尾

- [ ] 9.1 文档：架构图 + 脚本用法 + 双环境说明，补进 animal-action-survey §4.4 附录
- [ ] 9.2 向用户汇报：行为簇结果 + 线性探针指标
- [ ] 9.3 提交（feat: 前缀；数据资产不入库）

## 10. 延后任务（多猫数据出现时启用）

> BoxMOT 四候选（ByteTrack/OC-SORT/BoT-SORT/DeepSORT）已装 plf 备用；原理见 design D1c。

- [ ] 10.1 GT 制作：抽 3–5 段白天视频（含多猫），人工核对 track_id
- [ ] 10.2 固定检测源缓存 + 运行四候选
- [ ] 10.3 指标（IDF1/IDSW/碎片/平滑度）+ 选型报告（决定 CLI 默认跟踪器）
- [ ] 10.4 检测器侧误报抑制消融记录：阈值扫描已预跑——0.3→0.5 均无法抑制沙发超宽框（高置信检出），沙发漂移由渲染层尺寸离群过滤兜底；§4 多目标检测通过后升级为沙发框语义校验
