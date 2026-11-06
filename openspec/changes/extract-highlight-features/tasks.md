# Tasks

## Plan / Review

- [x] 1.1 读取 `项目要求.txt` 亮点抓取条目、`最终方案图.jpg`、现有 `petlib` 接口与 v1 配置。
- [x] 1.2 写 proposal / design / spec / tasks。
- [x] 1.3 用户 2026-11-02 直接指示实施（云端先不动、暂不提交），进入 Apply。

## 2. 实现

- [x] 2.1 `petlib/highlights/metrics.py`：亮度、对比度、运动能量（含全局补偿）、面积、质心。
- [x] 2.2 `petlib/highlights/sources.py`：PetSource（yolo_seg / track_json / none）、FaceSource（haar / none）。
- [x] 2.3 `petlib/highlights/actions.py`：时间轴读取、MMAction2 滑窗识别（懒加载）、同标签合并、云端复核标记。
- [x] 2.4 `petlib/highlights/aggregate.py`：采样循环、窗口汇总、时长与连续段。
- [x] 2.7 按用户修订删除端侧亮点候选（筛选归云端）。
- [x] 2.8 兼容 Python 3.8（端侧常见版本）；YOLO 跨类别 NMS（同一只猫被同时判为 cat/dog）。
- [x] 2.9 `scripts/render_highlight_demo.py`：载荷叠加回视频 + 拼图，供人工核对。
- [x] 2.5 `petlib/highlights/report.py`：`pet.highlight.v1` 载荷、确定性 event_id、outbox 原子写入。
- [x] 2.6 `scripts/extract_highlight_features.py` CLI。

## 3. 验证

- [x] 3.1 `scripts/test_highlight_features.py` 合成数据单元测试全部通过（2026-11-02 本地 15/15，
  含 Haar 级联加载；YOLO 与 MMAction2 路径未执行）。
- [x] 3.2 CLI 在 `--pet-source none --face none` 下对合成视频产出合法载荷并写入 outbox。
- [x] 3.4 （用户要求，本机 RTX 3060）单猫真实视频示例：YOLO11n-seg + Haar，结果见
  `docs/highlight_features.md`“本机示例”。
- [x] 3.5 （用户要求，本机）接入 v1 七类 X3D-S 行为滑窗：4 段单猫视频跑通，时间轴写入载荷，
  abnormal/低分段标云端复核；叠加图显示行为标签。
- [ ] 3.3 用更多未参与训练的单猫视频抽查露脸、面积与行为段，按真实分布回调阈值
  （服务器空闲后或继续在本机）。

## 4. 文档

- [x] 4.1 `docs/highlight_features.md`：字段定义、单位、默认阈值、用法、限制、待办。

## 范围限制

- [x] 5.1 确认未实现云端接收/上传、未从公网下载权重（yolo11n-seg.pt 与 X3D-S checkpoint
  从 4090 服务器只读复制，SHA-256 一致）、未训练、未在服务器上执行；本机推理仅限用户要求的示例。
- [x] 5.2 按用户指示提交（2026-11-02，`feat/highlight-features`），2026-11-06 推送 GitHub 并提 PR。
