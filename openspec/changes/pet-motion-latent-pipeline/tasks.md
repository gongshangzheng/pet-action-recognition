# Tasks: pet-motion-latent-pipeline

> **依赖**：本 change 依赖 `provision-a100-server`（plf 环境 + A100 算力）。依赖完成前：仅 1.6–1.9（petlib 接口骨架，本地纯代码）可先行；1.1–1.5 与 2.x/3.x/4.x 的执行类任务（需 plf 环境/A100）不得开工。
>
> **约定**：NPZ 关键点 schema = `keypoints (T,V,3) float16 + frame_inds + total_frames`（score 内嵌第三通道）；轨迹 JSON = `{track_id, boxes:[{frame,x1,y1,x2,y2,conf,interpolated}]}`。

## 0. 关卡 0A：猫居中预处理 Demo（用户验收点，先行）

> 顺序修正（用户指示）：先做检测/跟踪/居中裁剪并产出跟随视角视频交用户验收；关键点质量检查在验收过的跟随视频上进行（关卡 0B）。

- [ ] 0A.1 单段白天视频 spike（`event_20260806_120311.mp4`，384 帧 15fps）：
  - 抽样检测：每 10 帧跑 GroundingDINO（prompt=`"cat."`，box_threshold=0.3，plf 环境 transformers `GroundingDinoForObjectDetection`，权重经 hf-mirror 自动下载 `IDEA-Research/grounding-dino-tiny`）
  - 跟踪：检测框 IoU>0.3 关联成主轨迹（取累计置信度最高序列）；线性插值到全帧；滑动平均（窗口 5）平滑
  - 裁剪：尺寸锁定策略——track 前 N 次检出框 P75 ×1.2 锁定窗口边长（本示例段 ≈1234px），位置逐帧跟随；实际框 > 窗口×0.9 时临时放大防裁切并记录
  - 产出：`followcam.mp4` + 原图/跟随并排对比视频 + 检测框接触表 JPG
  - 验收：猫始终居中、无跳切；用户观看判定
- [ ] 0A.2 **用户验收**：不通过则管线方案重新评估（阻塞后续所有任务）

## 0b. 关卡 0B：关键点质量抽查（在 0A 验收通过的跟随视频上进行）

> 关键点检测方法不止一种：DLC 式（SuperAnimal）、MMPose 动物动物园（ViTPose/RTMPose/HRNet 的 AP-10K 变体）、SLEAP 式等，各有训练数据与骨架定义差异。petlib/keypoints 注册表内所有候选走同一评测，不预设胜负（选型标准见 spec「关键点提取器双候选对比选型」场景）。

- [ ] 0B.1 抽 5 段白天跟随视频，分别跑注册的候选提取器（至少：SuperAnimal-Quadruped、ViTPose-AP10K；可扩 RTMPose-AP10K/HRNet-AP10K）+ 叠加可视化
- [ ] 0B.2 出对比质量报告：各候选的置信度分布、时序抖动（相邻帧关键点位移方差）、点位合理性人工判定（通过者进关键点路线，多者通过则按 spec 选型标准定主用）
- [ ] 0B.3 范围备忘：夜间红外 45 段本 change 不处理（二期，需 YOLO11 夜视微调 + IR 关键点验证）

## 1. 接口骨架 + 离线猫居中预处理管线

> 1.6–1.9 为接口骨架，**先于 1.1–1.5 执行**；1.1–1.5 的具体实现全部落位在 petlib 接口之下。

- [ ] 1.6 建 `petlib/` 包：`schemas.py`（Detection/Track/KeypointSequence dataclass + NPZ schema 常量）；验收 = `python -c "import petlib"` 零重依赖通过 + pytest -k schemas 通过
- [ ] 1.7 三类抽象接口 `detection/base.py`（`Detector.detect(img, classes)->list[Detection]`）、`tracking/base.py`（`Tracker.update(dets, frame_idx)->list[Track]` + `finalize()`）、`keypoints/base.py`（`KeypointExtractor.extract(crop_seq)->KeypointSequence`）+ `registry.py` 工厂（`create(kind, name, **cfg)`）+ `pipeline.yaml` 配置选择；验收 = `create('tracker','byte_track')` 返回实例
- [ ] 1.8 实现落位：`detection/grounding_dino.py`（transformers 懒加载）、`tracking/{byte_track,oc_sort,bot_sort,deep_sort}.py`（官方仓适配）、`keypoints/{superanimal,vitpose_ap10k}.py`（deeplabcut 未装者占位 + 契约测试 xfail 标记）
- [ ] 1.9 `contract_tests.py`：fixture 帧 → 对所有注册实现跑接口冒烟 + 输出 schema 校验（pytest 参数化）；每个新实现注册后必须先过契约
- [ ] 1.1 `scripts/plf_detect_track.py`（CLI，petlib 编排）：`--input <video> --out tracks.json --detector grounding_dino --tracker byte_track --sample-every 10`；流程 = 抽样检测 → 跟踪 → 全帧插值 → 卡尔曼/滑平均平滑 → 轨迹 JSON + 处理报告（检出率/插值率，分昼夜统计字段预留）
- [ ] 1.2 `scripts/make_followcam.py`：轨迹 JSON + 原视频 → `followcam.mp4`（尺寸锁定策略，见 design D1）+ 并排对比视频 + 接触表；参数：外扩 1.2×、平滑窗口 5、防裁切保护阈值 0.9
- [ ] 1.3 `scripts/extract_keypoints_from_tracks.py`：轨迹 + 原视频 → 每轨迹关键点 NPZ（经 petlib/keypoints 注册实现，默认关卡 0B 胜出者）
- [ ] 1.4 全量批处理白天段（34/79）：循环 1.1–1.3，产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 训练格式，供 9 月标注微调）
- [ ] 1.5 批处理报告：逐段检出率/插值率/时长覆盖表；异常段清单（插值率 >30% 告警）

## 2. 运动隐空间（条件启动：零训练基线不达标时才训）

> 依 design D3 实施次序：先跑 2.1 零训练基线（B-SOiD 式），「人工可命名率 ≥60% 且簇不碎」则 2.2–2.4 降级为可选增强；不达标才启动 VQ-VAE 训练。

- [ ] 2.1 零训练基线 `scripts/discover_behaviors_baseline.py`：关键点 → 手工运动学特征（逐帧关节速度 V×2、选定关节角、成对距离子集；窗口标准化去机位/尺度）→ UMAP(n_neighbors=30) → HDBSCAN → 行为簇 + 代表帧导出 + **可命名率报告**（人工抽 30 簇判定）
- [ ] 2.2（条件）`configs/motion_latent/`：模型定义 E_mot(1D CNN+Transformer, 48×34→12×32) / E_id(池化+MLP→64) / VQ 码本(K=512,d=32) / G 解码器；损失 = L1 重建 + 速度 L1 + VQ + InfoNCE(s, **track 级监督**) + 0.01‖Δz‖² 平滑
- [ ] 2.3（条件）训练数据生成：cats + pet_action_mammal_v0 + live 录像的关键点窗口（48/24 滑窗，**按源视频分组切分**，目标 ≥15 万窗口）
- [ ] 2.4（条件）pet/A100 单卡训练至收敛（≤4h），码本利用率 ≥50%（否则重置机制），保存 checkpoint + 曲线

## 3. 评测：L3 发现 + L1 探针

- [ ] 3.1 `scripts/discover_behaviors.py`：聚类 → 各簇代表帧导出 → 人工命名表（输入兼容：零训练基线的运动学特征簇 / VQ token 簇）
- [ ] 3.2 NMI/ARI 报告（聚类 vs 现有 5 类人工标注）
- [ ] 3.3 `scripts/train_linear_probe.py`：冻结编码器线性探针（5 类），top1 + 与 VideoMAEv2 基线差值；判定：≥ 基线 80% 则路线成立
- [ ] 3.4 可遍历性检查：隐码插值序列渲染抽查
- [ ] 3.5 HQSAM 消融实验（可选阶段）：mask 清洗 crop vs 原始 crop 各训线性探针对比，决定 mask 是否进入主链

## 4. 抽查式推理 CLI

- [ ] 4.0 `petlib/actions/`：ActionClassifier 接口 + 两个实现（motion_latent_probe / mmaction2_model 包装现有 checkpoint），抽查管线动作头可配置切换
- [ ] 4.1 `scripts/spot_check_actions.py`：输入摄像头+时间段 → 拉录像 → 预处理 → 隐码 → 动作报告（JSON/Markdown：标签/起止秒/track_id/**登记身份（哪只猫）**/置信度/疑似新动作提示/猫在场率）
- [ ] 4.1b `scripts/register_cats.py`：猫个体档案登记（每猫 3–5 张清晰 crop → 特征 embedding 入库）+ 检索识别函数（供 4.1 调用），标注未登记个体为「未知猫 #N」
- [ ] 4.2 端到端联调：抽 3 个真实时段（含 1 个无猫时段）出报告
- [ ] 4.3 L2 边界误差抽查：动作码突变点 = 切换边界，误差须在滑窗粒度 ±1.5s 内

## 5. 收尾

- [ ] 5.1 文档：管线架构图 + 各脚本用法 + 三环境（pet/plf/live）说明，补进 `papers/docs/animal-action-survey.md` §4.4 附录
- [ ] 5.2 向用户汇报：隐空间聚类发现的行为簇结果 + 线性探针指标
- [ ] 5.3 提交（feat: 前缀；脚本/config/文档；数据资产不入库）
