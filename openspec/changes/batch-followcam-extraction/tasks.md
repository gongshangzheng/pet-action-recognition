# Tasks: batch-followcam-extraction

> 总管：`pet-motion-latent-pipeline`。前置：`multi-object-detect-gate` 验收通过（多 prompt 清单 + 状态层规则定稿）。
> 严格按编号顺序执行；每次 GPU 任务前 `nvidia-smi` 查占用。

- [ ] 1.1 `scripts/plf_detect_track.py`：多 prompt 抽样检测（每 10 帧）+ 插值平滑 + **逐帧运动校正**（design B2：背景建模前景 mask 融合，校正幅度上限，校正量落盘）→ 轨迹 JSON（猫框 + 家具框 + 空间状态序列）
- [x] 1.2 运动校正消融验证完成（2026-09-15，**用户验收“效果很不错”**）：三轮迭代 v1（缩框切猁 bug）→ v2（只扩不缩+覆盖门槛）→ v3（EMA 相机路径，滞后否决）→ v4（锚点精确+半余弦窗偏移）→ v5 参数定稿（off-alpha 0.6 / off-max-v 5%帧宽 / 覆盖门槛 0.2）；最终实测：校正触发 12.0%，偏移 max 108px，锚点帧像素级一致；三联对比视频（原片/interp-only/motion-corrected）脚本 `scripts/plf_compare_followcam3.py`
- [ ] 1.3 `scripts/make_followcam.py`：轨迹 JSON → follow_adaptive 跟随视频（尺寸离群过滤内置）+ H.264 直写（petlib H264VideoWriter）
- [x] 1.4 ~~关键点 NPZ~~（**2026-09-15 用户裁定裁剪**：MC 跟随视角实测 mean_conf 0.367、>0.5 帧仅 0.2%、四肢点 <0.25、叠加抖动不可用 → 关键点整体移出管线；脚本 `extract_keypoints_from_tracks.py` 保留入库备查，批处理不产出 NPZ）
- [ ] 1.5 全量循环 34 段白天视频：产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 格式）+ 家具框轨迹
- [ ] 1.6 批处理报告：逐段检出率/插值率/校正率/离群剔除统计；插值率 >30% 告警清单 → 用户过目后 archive
