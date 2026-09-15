# Tasks: batch-followcam-extraction

> 总管：`pet-motion-latent-pipeline`。前置：`multi-object-detect-gate` 验收通过（多 prompt 清单 + 状态层规则定稿）。
> 严格按编号顺序执行；每次 GPU 任务前 `nvidia-smi` 查占用。

- [ ] 1.1 `scripts/plf_detect_track.py`：多 prompt 抽样检测（每 10 帧）+ 插值平滑 + **逐帧运动校正**（design B2：背景建模前景 mask 融合，校正幅度上限，校正量落盘）→ 轨迹 JSON（猫框 + 家具框 + 空间状态序列）
- [ ] 1.2 运动校正消融验证：074451 段「仅插值 vs 插值+校正」两版跟随视频 + 校正率统计 → 用户抽检确认框覆盖改善
- [ ] 1.3 `scripts/make_followcam.py`：轨迹 JSON → follow_adaptive 跟随视频（尺寸离群过滤内置）+ H.264 直写（petlib H264VideoWriter）
- [ ] 1.4 `scripts/extract_keypoints_from_tracks.py`：crop-first 关键点 NPZ（HRNet-W32-AP10K，辅助信号用途）
- [ ] 1.5 全量循环 34 段白天视频：产出 `datasets/cats/followcam/`、`keypoints/`、伪标注框包（YOLO 格式）+ 家具框轨迹
- [ ] 1.6 批处理报告：逐段检出率/插值率/校正率/离群剔除统计；插值率 >30% 告警清单 → 用户过目后 archive
