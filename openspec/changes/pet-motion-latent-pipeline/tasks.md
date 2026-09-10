# Tasks: pet-motion-latent-pipeline

## 0. 关卡 0：白天关键点质量抽查（低风险，快速验证）

- [ ] 0.1 抽 5 段白天视频跑 SuperAnimal 提取 + `visualize_keypoints.py` 叠加可视化
- [ ] 0.2 出质量报告：置信度分布、点位合理性人工判定（通过 → 白天段全量进关键点路线）
- [ ] 0.3 范围备忘：夜间红外 45 段本 change 不处理（二期，需 YOLO11 夜视微调 + IR 关键点验证）

## 1. 离线猫居中预处理管线

- [ ] 1.1 pet 新建 conda env `plf`（GroundingDINO/HQSAM/ViTPose 依赖，锁版本 README）
- [ ] 1.2 `scripts/plf_detect_track.py`：检测+跟踪管线，跟踪器可插拔（统一输入输出接口：检测 JSON → 轨迹 JSON）
- [ ] 1.2b 跟踪器对比实验：固定 GroundingDINO 白天检出，3–5 段人工核对 GT，比 ByteTrack/OC-SORT/BoT-SORT/DeepSORT 的 IDF1/IDSW/碎片数/平滑度，记录选型结论
- [ ] 1.3 `scripts/make_followcam.py`：轨迹 → 猫居中稳定裁剪视频（768×768，窗口渐变防跳切，外扩 1.2×）
- [ ] 1.4 `scripts/extract_keypoints_from_tracks.py`：轨迹裁剪区域 → SuperAnimal 关键点 NPZ（复用既有链路）
- [ ] 1.5 全量批处理白天段（34/79）：产出跟随视频 + 关键点 + 伪标注框 + 处理报告（检出率、插值率）

## 2. 运动隐空间提取器训练

- [ ] 2.1 `configs/motion_latent/`：模型定义（E_mot/E_id/VQ 码本 K=512/G）+ 损失（重建+速度+VQ+InfoNCE+平滑）
- [ ] 2.2 `scripts/train_motion_latent.py`：自监督训练循环（窗口 48/stride 24，按源视频分组切分，码本利用率监控+重置）
- [ ] 2.3 训练数据生成：cats 717 clips + pet_action_mammal_v0 + live 录像的关键点窗口（目标 ≥15 万窗口）
- [ ] 2.4 pet 单卡训练至收敛（≤4h），保存隐空间 checkpoint + 训练曲线

## 3. 评测：L3 发现 + L1 探针

- [ ] 3.1 `scripts/discover_behaviors.py`：token 直方图 → 聚类 → 各簇代表帧导出 → 人工命名表
- [ ] 3.2 NMI/ARI 报告（聚类 vs 现有 5 类人工标注）
- [ ] 3.3 `scripts/train_linear_probe.py`：冻结编码器线性探针（5 类），top1 + 与 VideoMAEv2 基线差值
- [ ] 3.4 可遍历性检查：隐码插值序列渲染抽查
- [ ] 3.5 HQSAM 消融实验（可选阶段）：mask 清洗 crop vs 原始 crop 各训线性探针对比，决定 mask 是否进入主链

## 4. 抽查式推理 CLI

- [ ] 4.1 `scripts/spot_check_actions.py`：输入摄像头+时间段 → 预处理 → 隐码 → 动作报告（JSON/Markdown：标签/起止秒/track_id/置信度/疑似新动作提示/猫在场率）
- [ ] 4.2 端到端联调：抽 3 个真实时段（含 1 个无猫时段）出报告
- [ ] 4.3 L2 边界误差抽查：滑窗粒度 ±1.5s 内验证

## 5. 收尾

- [ ] 5.1 文档：管线架构图 + 各脚本用法 + 三环境（pet/plf/live）说明，补进 `papers/docs/animal-action-survey.md` §4.4 附录
- [ ] 5.2 向用户汇报：隐空间聚类发现的行为簇结果 + 线性探针指标
- [ ] 5.3 提交（feat: 前缀；脚本/config/文档；数据资产不入库）
