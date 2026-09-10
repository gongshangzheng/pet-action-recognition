# Tasks: pet-motion-latent-pipeline

> **依赖**：本 change 依赖 `provision-a100-server`（plf 环境 + A100 算力）。依赖完成前：仅 §1 接口骨架（本地纯代码）可先行；§2/§3/§4 的执行类任务（需 plf 环境/A100）不得开工。
>
> **约定**：NPZ 关键点 schema = `keypoints (T,V,3) float16 + frame_inds + total_frames`（score 内嵌第三通道）；轨迹 JSON = `{track_id, boxes:[{frame,x1,y1,x2,y2,conf,interpolated}]}`；示例视频 = `event_20260806_120311.mp4`（2880×1620@15fps，384 帧，白天）。

## 0. 关卡 0A：猫居中预处理 Demo（用户验收点，先行）

- [ ] 0.1 示例视频传输：scp 至 A100 `~/data/cats/`，ffprobe 校验帧数/分辨率
- [ ] 0.2 GroundingDINO 权重就位：plf 环境经 hf-mirror 下载 `IDEA-Research/grounding-dino-tiny`，单帧推理冒烟
- [ ] 0.3 抽样检测：每 10 帧跑 GroundingDINO（prompt=`"cat."`，box_threshold=0.3）→ 39 帧检测框
- [ ] 0.4 轨迹关联：IoU>0.3 逐帧关联 → 主轨迹（累计置信度最高）；跨帧断链用 IoU 插值续接
- [ ] 0.5 轨迹插值到全帧 + 滑动平均（窗口 5）平滑 → 平滑轨迹 JSON
- [ ] 0.6 虚拟摄像机渲染：尺寸锁定策略（前 N 次检出框 P75×1.2，实测约 1234px）+ 防裁切保护（实际框>窗口×0.9 临时放大并记录）→ `followcam.mp4`
- [ ] 0.7 并排对比视频（左原图+框叠加，右跟随视角）+ 检测框接触表 JPG
- [ ] 0.8 产物回传本地，交用户观看
- [ ] 0.9 **用户验收**：猫始终居中、无跳切抖动；不通过则方案重评（阻塞后续）

## 0b. 关卡 0B：关键点质量抽查（在 0A 验收通过的跟随视频上进行）

> 关键点检测方法不止一种：DLC 式（SuperAnimal）、MMPose 动物动物园（ViTPose/RTMPose/HRNet 的 AP-10K 变体）、SLEAP 式等，各有训练数据与骨架定义差异。petlib/keypoints 注册表内所有候选走同一评测，不预设胜负（选型标准见 spec「关键点提取器双候选对比选型」场景）。

- [ ] 0b.1 抽 5 段白天跟随视频，分别跑注册的候选提取器（至少：SuperAnimal-Quadruped、ViTPose-AP10K；可扩 RTMPose-AP10K/HRNet-AP10K）+ 叠加可视化
- [ ] 0b.2 出对比质量报告：各候选的置信度分布、时序抖动（相邻帧关键点位移方差）、点位合理性人工判定（通过者进关键点路线，多者通过则按 spec 选型标准定主用）
- [ ] 0b.3 范围备忘：夜间红外 45 段本 change 不处理（二期，需 YOLO11 夜视微调 + IR 关键点验证）

## 1. petlib 接口骨架（本地纯代码，可先于依赖完成）

- [ ] 1.1 `petlib/schemas.py`：dataclass `Detection(frame,box,conf,cls)` / `Track(track_id,boxes,...)` / `KeypointSequence(kp,score,frame_inds,total_frames,source)` + NPZ/轨迹 JSON schema 常量；验收 = `import petlib` 零重依赖 + pytest -k schemas 通过
- [ ] 1.2 `petlib/detection/base.py`：`Detector(ABC).detect(img_bgr, classes) -> list[Detection]`；`grounding_dino.py`（transformers 懒加载实现）
- [ ] 1.3 `petlib/tracking/base.py`：`Tracker(ABC).update(dets, frame_idx) -> list[Track]` + `finalize()`；`byte_track.py / oc_sort.py / bot_sort.py / deep_sort.py` 四个适配实现
- [ ] 1.4 `petlib/keypoints/base.py`：`KeypointExtractor(ABC).extract(crop_seq) -> KeypointSequence`；`superanimal.py`、`vitpose_ap10k.py` 实现
- [ ] 1.5 `petlib/registry.py`：`create(kind, name, **cfg)` 工厂 + `pipeline.yaml` 配置选择；验收 = `create('tracker','byte_track')` 返回实例

## 2. 跟踪器对比选型实验（design D1）

- [ ] 2.1 GT 制作：抽 3–5 段白天视频（含 1 段多猫），人工核对/修正各候选跟踪器输出的 track_id，形成小样本 GT
- [ ] 2.2 固定检测源：同一份 GroundingDINO 白天检出缓存作为四候选的共同输入（排除检测变量）
- [ ] 2.3 运行四候选（ByteTrack/OC-SORT/BoT-SORT/DeepSORT），逐段产出轨迹
- [ ] 2.4 指标计算：IDF1（主）、IDSW、轨迹碎片数、框平滑度（相邻帧中心位移方差）
- [ ] 2.5 选型报告：对比表 + 判定标准（IDF1 优先，碎片/抖动为辅）+ 结论（决定 §4 CLI 默认跟踪器）

## 3. 关键点提取器对比选型实验（关卡 0B 的正式化，design D2）

- [ ] 3.1 候选实现注册：superanimal.py、vitpose_ap10k.py 通过契约测试（1.4 完成后自动满足）
- [ ] 3.2 同 5 段白天跟随视频跑双候选，产出对比报告（置信度分布/时序抖动/可视化抽检/下游线性探针 top1）
- [ ] 3.3 选型结论记录（探针 top1 为主判据；平手取 SuperAnimal 因与现有脚本兼容），主用提取器写进 pipeline.yaml

## 4. 离线猫居中预处理管线（全量白天段）

- [ ] 4.1 `scripts/plf_detect_track.py` CLI 编排（petlib 组装：检测→跟踪→插值→平滑→轨迹 JSON + 处理报告检出率/插值率）
- [ ] 4.2 `scripts/make_followcam.py`：轨迹 JSON + 原视频 → followcam.mp4（CameraPolicy 可配置，默认 follow_locked，design D1）+ 并排对比视频
- [ ] 4.3 `scripts/extract_keypoints_from_tracks.py`：轨迹 + 原视频 → 每轨迹关键点 NPZ（默认关卡 0B 胜出提取器）
- [ ] 4.4 全量批处理白天段（34/79）：循环 4.1–4.3，产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 训练格式）
- [ ] 4.5 批处理报告：逐段检出率/插值率/时长覆盖表；插值率 >30% 的异常段告警清单

## 5. 运动隐空间（条件启动：零训练基线不达标时才训）

> 依 design D3 实施次序：先跑 5.1–5.3 零训练基线（B-SOiD 式），「人工可命名率 ≥60% 且簇不碎」则 5.4–5.6 降级为可选增强；不达标才启动 VQ-VAE 训练。

- [ ] 5.1 零训练基线特征：关键点 → 手工运动学特征（逐帧关节速度 V×2、选定关节角、成对距离子集；窗口标准化去机位/尺度）
- [ ] 5.2 零训练基线聚类：UMAP(n_neighbors=30) → HDBSCAN → 行为簇
- [ ] 5.3 可命名率报告：导出各簇代表帧，人工抽 30 簇判定「能说出猫在干嘛」的占比
- [ ] 5.4（条件）`configs/motion_latent/`：模型定义 E_mot(1D CNN+Transformer, 48×34→12×32) / E_id(池化+MLP→64) / VQ 码本(K=512,d=32) / G 解码器；损失 = L1 重建 + 速度 L1 + VQ + InfoNCE(s, **track 级监督**) + 0.01‖Δz‖² 平滑
- [ ] 5.5（条件）训练数据生成：cats + pet_action_mammal_v0 + live 录像关键点窗口（48/24 滑窗，**按源视频分组切分**，目标 ≥15 万窗口）
- [ ] 5.6（条件）A100 单卡训练至收敛（≤4h），码本利用率 ≥50%（否则重置机制），保存 checkpoint + 曲线

## 6. 评测：L3 发现 + L1 探针

- [ ] 6.1 `scripts/discover_behaviors.py`：聚类 → 各簇代表帧导出 → 人工命名表（输入兼容：零训练基线特征簇 / VQ token 簇）
- [ ] 6.2 NMI/ARI 报告（聚类 vs 现有 5 类人工标注）
- [ ] 6.3 `scripts/train_linear_probe.py`：冻结编码器线性探针（5 类），top1 + 与 VideoMAEv2 基线差值；判定：≥ 基线 80% 则路线成立
- [ ] 6.4 可遍历性检查：隐码插值序列渲染抽查
- [ ] 6.5 HQSAM 消融实验（可选阶段）：mask 清洗 crop vs 原始 crop 各训线性探针对比，决定 mask 是否进入主链
- [ ] 6.6 虚拟摄像机策略消融：fixed / follow_locked / follow_adaptive 三种 CameraPolicy 各产出跟随视频，各训线性探针对比 top1 + 人工观感抽查，定主用策略

## 7. 抽查式推理 CLI

- [ ] 7.1 `scripts/spot_check_actions.py`：输入摄像头+时间段 → 拉录像 → 预处理 → 隐码 → 动作报告（JSON/Markdown：标签/起止秒/track_id/**登记身份（哪只猫）**/置信度/疑似新动作提示/猫在场率）
- [ ] 7.2 `scripts/register_cats.py`：猫个体档案登记（每猫 3–5 张清晰 crop → 特征 embedding 入库）+ 检索识别函数（供 7.1 调用），标注未登记个体为「未知猫 #N」
- [ ] 7.3 端到端联调：抽 3 个真实时段（含 1 个无猫时段）出报告
- [ ] 7.4 L2 边界误差抽查：动作码突变点 = 切换边界，误差须在滑窗粒度 ±1.5s 内

## 8. 收尾

- [ ] 8.1 文档：管线架构图 + 各脚本用法 + 多环境（pet/plf/A100/live）说明，补进 `papers/docs/animal-action-survey.md` §4.4 附录
- [ ] 8.2 向用户汇报：隐空间聚类发现的行为簇结果 + 线性探针指标
- [ ] 8.3 提交（feat: 前缀；脚本/config/文档；数据资产不入库）
