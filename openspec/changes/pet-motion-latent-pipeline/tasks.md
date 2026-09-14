# Tasks: pet-motion-latent-pipeline

> **依赖与执行机**：本 change 在 **pet** 上执行（plf 独立 conda 环境，与 mmaction2 的 pet 环境隔离；A100 已降级为备用算力）。**每次使用 GPU 前必须先 `nvidia-smi` 检查占用**：两卡都被占则等待或与占用者协调，禁止抢占；选空闲卡以 `CUDA_VISIBLE_DEVICES=cuda:N` 指定。依赖完成前：仅 §1 接口骨架（本地纯代码）可先行。
>
> **执行顺序 = 编号顺序（§1 → §10）**。§4 的用户验收是硬关卡，未通过则回退 §2 重新评估。
>
> **约定**：NPZ 关键点 schema = `keypoints (T,V,3) float16 + frame_inds + total_frames`（score 内嵌第三通道）；轨迹 JSON = `{track_id, boxes:[{frame,x1,y1,x2,y2,conf,interpolated}]}`。

## 1. petlib 接口骨架（本地纯代码）

- [x] 1.1 pet 建 plf 环境：clone pet 环境（torch 2.1.2+cu121）+ pip install transformers==4.49.0 accelerate；验证 pet 环境 mmcv 2.1.0 不受影响；GPU 占用检查纪律生效
- [x] 1.2 `petlib/schemas.py`：dataclass `Detection(frame,box,conf,cls)` / `Track(track_id,boxes,...)` / `KeypointSequence(kp,score,frame_inds,total_frames,source)` + NPZ/轨迹 JSON schema 常量；验收 = `import petlib` 零重依赖 + pytest -k schemas 通过
- [x] 1.3 `petlib/detection/base.py`：`Detector(ABC).detect(img_bgr, classes) -> list[Detection]`；`grounding_dino.py`（transformers 懒加载实现）
- [x] 1.4 `petlib/tracking/base.py`：`Tracker(ABC).update(dets, frame_idx) -> list[Track]` + `finalize()`；`byte_track.py / oc_sort.py / bot_sort.py / deep_sort.py` 四个适配实现
- [x] 1.5 `petlib/keypoints/base.py`：`KeypointExtractor(ABC).extract(crop_seq) -> KeypointSequence`；`superanimal.py`、`vitpose_ap10k.py` 实现
- [x] 1.6 `petlib/registry.py`：`create(kind, name, **cfg)` 工厂 + `pipeline.yaml` 配置选择；验收 = `create('tracker','byte_track')` 返回实例
- [x] 1.7 `petlib/contract_tests.py`：契约冒烟测试（fixture 帧 → 接口调用 → schema 校验），pytest 参数化

## 2. 跟踪器对比选型实验（四候选：ByteTrack/OC-SORT/BoT-SORT/DeepSORT，BoxMOT 官方实现）

> 沙发误检漂移的抑制已由渲染层的尺寸离群过滤实现（side > 1.8×中位 → 剔除+插值，见 6.2）；检测门控方案经评审否决（design D1b 记录）。

- [ ] 2.1 GT 制作：抽 3–5 段白天视频（含 1 段多猫），人工核对/修正 track_id，形成小样本 GT
- [ ] 2.2 固定检测源：同一份 GroundingDINO 白天检出缓存作为所有候选的共同输入（排除检测变量）
- [ ] 2.3 运行四候选，逐段产出轨迹
- [ ] 2.4 指标计算：IDF1（主）、IDSW、轨迹碎片数、框平滑度（相邻帧中心位移方差）
- [ ] 2.5 选型报告：对比表 + 判定标准（IDF1 优先，碎片/抖动为辅）+ 结论（决定 §6 CLI 默认跟踪器）

## 3. 跟踪器对比选型（五候选同台）

- [ ] 3.1 GT 制作：抽 3–5 段白天视频（含 1 段多猫），人工核对/修正 track_id，形成小样本 GT
- [ ] 3.2 固定检测源：同一份 GroundingDINO 白天检出缓存作为所有候选的共同输入（排除检测变量）
- [ ] 3.3 运行四候选，逐段产出轨迹
- [ ] 3.4 指标计算：IDF1（主）、IDSW、轨迹碎片数、框平滑度（相邻帧中心位移方差）
- [ ] 3.4b 检测器侧误报抑制消融：阈值扫描 0.3/0.4/0.5 × prompt 变体（"cat." / "cat. sofa." 负提示实验），画漏检率 vs 误报率权衡曲线（已预跑：阈值无法抑制沙发超宽框——见会话记录，沙发漂移由渲染层尺寸离群过滤兜底）
- [ ] 3.5 选型报告：四候选 + 检测器侧扫描同台对比表 + 判定标准（IDF1 优先，碎片/抖动为辅）+ 结论（决定 §6 CLI 默认跟踪器）

## 4. 猫居中 Demo 重做 + 用户验收（硬关卡）

- [ ] 4.1 用 §3 选型胜出的跟踪器重跑两段 Demo（120311 + 074451，follow_adaptive 裁剪，design D1 CameraPolicy 默认）
- [ ] 4.2 ffmpeg 转 H.264（mp4v 编码 QuickTime 不支持）+ 产物回传本地
- [ ] 4.3 **用户验收**：猫始终居中、无跳切抖动、**无沙发漂移**；不通过则回退 §2 重新评估（阻塞 §5 之后所有任务）

## 5. 关键点提取器对比选型（在验收通过的跟随视频上进行）

> 关键点检测方法不止一种：DLC 式（SuperAnimal）、MMPose 动物动物园（ViTPose/RTMPose/HRNet 的 AP-10K 变体）、SLEAP 式等。petlib/keypoints 注册表内所有候选走同一评测，不预设胜负（选型标准见 spec「关键点提取器双候选对比选型」场景）。

- [ ] 5.1 抽 5 段白天跟随视频，分别跑注册候选（至少 SuperAnimal-Quadruped、ViTPose-AP10K；可扩 RTMPose-AP10K/HRNet-AP10K）+ 叠加可视化
- [ ] 5.2 对比质量报告：置信度分布、时序抖动（相邻帧关键点位移方差）、点位合理性人工判定
- [ ] 5.3 选型结论（多者通过按 spec 标准定主用）
- [ ] 5.4 范围备忘：夜间红外 45 段本 change 不处理（二期，需 YOLO11 夜视微调 + IR 关键点验证）

## 6. 全量批处理（白天段 34/79）

- [ ] 6.1 `scripts/plf_detect_track.py` CLI 编排（petlib 组装：检测→跟踪→插值→平滑→轨迹 JSON + 检出率/插值率报告）
- [ ] 6.2 `scripts/make_followcam.py`：轨迹 JSON + 原视频 → followcam.mp4（CameraPolicy 可配置，默认 follow_adaptive，design D1）+ 并排对比视频
- [ ] 6.3 `scripts/extract_keypoints_from_tracks.py`：轨迹 + 原视频 → 每轨迹关键点 NPZ（§5 选型胜出者）
- [ ] 6.4 全量循环 34 段：产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 训练格式）+ ffmpeg 转 H.264
- [ ] 6.5 批处理报告：逐段检出率/插值率/时长覆盖表；插值率 >30% 告警清单

## 7. 运动隐空间（条件启动：零训练基线不达标时才训）

> 依 design D3 实施次序：先跑 7.1–7.3 零训练基线（B-SOiD 式），「人工可命名率 ≥60% 且簇不碎」则 7.4–7.6 降级为可选增强；不达标才启动 VQ-VAE 训练。

- [ ] 7.1 零训练基线特征：关键点 → 手工运动学特征（逐帧关节速度 V×2、选定关节角、成对距离子集；窗口标准化去机位/尺度）
- [ ] 7.2 零训练基线聚类：UMAP(n_neighbors=30) → HDBSCAN → 行为簇
- [ ] 7.3 可命名率报告：导出各簇代表帧，人工抽 30 簇判定「能说出猫在干嘛」的占比
- [ ] 7.4（条件）`configs/motion_latent/`：模型定义 E_mot(1D CNN+Transformer, 48×34→12×32) / E_id(池化+MLP→64) / VQ 码本(K=512,d=32) / G 解码器；损失 = L1 重建 + 速度 L1 + VQ + InfoNCE(s, **track 级监督**) + 0.01‖Δz‖² 平滑
- [ ] 7.5（条件）训练数据生成：cats + pet_action_mammal_v0 + live 录像关键点窗口（48/24 滑窗，**按源视频分组切分**，目标 ≥15 万窗口）
- [ ] 7.6（条件）pet 空闲卡训练至收敛（≤4h，开跑前 nvidia-smi 查占用），码本利用率 ≥50%（否则重置机制），保存 checkpoint + 曲线

## 8. 评测：L3 发现 + L1 探针 + 消融

- [ ] 8.1 `scripts/discover_behaviors.py`：聚类 → 各簇代表帧导出 → 人工命名表（输入兼容：零训练基线特征簇 / VQ token 簇）
- [ ] 8.2 NMI/ARI 报告（聚类 vs 现有 5 类人工标注）
- [ ] 8.3 `scripts/train_linear_probe.py`：冻结编码器线性探针（5 类），top1 + 与 VideoMAEv2 基线差值；判定：≥ 基线 80% 则路线成立
- [ ] 8.4 可遍历性检查：隐码插值序列渲染抽查
- [ ] 8.5 HQSAM 消融实验（可选阶段）：mask 清洗 crop vs 原始 crop 各训线性探针对比，决定 mask 是否进入主链
- [ ] 8.6 虚拟摄像机策略消融：follow_adaptive（已出结果）vs follow_locked vs fixed 各产出跟随视频，各训线性探针对比 top1 + 人工观感抽查——**检验「尺寸锁定保留距离线索」假设是否成立**，定主用策略

## 9. 抽查式推理 CLI

- [ ] 9.1 `scripts/spot_check_actions.py`：输入摄像头+时间段 → 拉录像 → 预处理 → 隐码 → 动作报告（JSON/Markdown：标签/起止秒/track_id/**登记身份（哪只猫）**/置信度/疑似新动作提示/猫在场率）
- [ ] 9.2 `scripts/register_cats.py`：猫个体档案登记（每猫 3–5 张清晰 crop → 特征 embedding 入库）+ 检索识别函数（供 9.1 调用），标注未登记个体为「未知猫 #N」
- [ ] 9.3 端到端联调：抽 3 个真实时段（含 1 个无猫时段）出报告
- [ ] 9.4 L2 边界误差抽查：动作码突变点 = 切换边界，误差须在滑窗粒度 ±1.5s 内

## 10. 收尾

- [ ] 10.1 文档：管线架构图 + 各脚本用法 + 双环境（pet 的 mmaction2 env / plf）说明，补进 `papers/docs/animal-action-survey.md` §4.4 附录
- [ ] 10.2 向用户汇报：隐空间聚类发现的行为簇结果 + 线性探针指标
- [ ] 10.3 提交（feat: 前缀；脚本/config/文档；数据资产不入库）
