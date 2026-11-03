# 实验证据

### 2026-11-03：实验启动与资产核验（`gdino-crop-20261103a`）

- **skill 闸门**：已加载 `openspec-apply-change`、`experiment`、`remote-ops`、`training`、`testing`、`datasets`、`remote-server-discipline` 和 `remote-servers`。
- **批准范围**：用户指示开始推进远程实验。沿用 change 中的 A 原视频、B GroundingDINO 空间裁剪、C 相同检测缓存加像素运动校正三臂，七个类别、日期隔离划分、共同样本和测试前冻结规则不变。
- **远程路径**：`/home/wyy/pet-final-1` 不存在；`/home/wyy/pet-final-v1` 存在且是独立 Git worktree，`/home/wyy/pet-final` 是主工作树。旧报告所述共享数据、索引、权重和结果的链接关系成立。
- **资源预检**：2026-11-03 20:00（Asia/Shanghai）GPU 0 有 Python 进程占用约 14,842 MiB；GPU 1 为 0 MiB 且利用率 0%，load 5.72/24 核，可用内存约 113 GiB，根盘剩余约 68 GiB。实验固定使用 GPU 1，每次重活前重新预检。
- **数据**：`cat_raw` 为 2,737 个视频、9.4 GiB；源区间表哈希为 `80da23af3c6a6db4bac739fc2c1dc8714b8b5dc063b55abe7c9762932eeb04ff`。
- **索引**：train/val/test 为 1,664/604/442，哈希分别为 `073350c27fbda36c4a931fb0852f20a495023cfe7298e2350c677dfa9962751c`、`21b7bb44d8450d210bb9a73d9f951ec8e3a571ab97a79e379d5b487c6e2eb1d6`、`058c08bcd78554d70714533140d712c8e1db50c5398d199d711be61653d4096e`，与历史记录一致。
- **历史锚点**：旧七类 VideoMAEv2-B 最佳 checkpoint 为 epoch 12，SHA-256 `39a1baa176d66b85244dde40521b11d05ed84f5a4815d64038122454c0e518ae`；历史 val top-1/macro-F1 为 85.93%/70.97%，test 为 81.90%/67.66%。这些是既有测试集复验锚点，不是本轮结果。
- **目标有效性**：区间内出现无可靠猫检测、超过两个检测步长的缺口、多猫目标不明或狗时，保守排除并记录原因。像素低运动不用于判定无猫；当前检测结果也不能区分真实无猫与探测器漏检。
- **下一步**：实现低内存检测、B/C 同步渲染、共同索引、三臂训练与冻结评测；先做单视频烟测和用户可见的小批质检，不直接启动 20-epoch 全量训练。
