# Design：亮点抓取特征提取

## D1 采样与分辨率

- 按 `analysis_fps`（默认 5）从原视频等间隔取帧，原视频 15 fps 时即每 3 帧取 1 帧；
  每个采样点代表 `1 / analysis_fps` 秒，用于累计时长。
- 取到的帧等比缩放到 `analysis_width`（默认 960）再计算；公司/本地猫视频为
  2880×1620，全分辨率逐帧算没有必要。面积占比是比例量，与缩放无关。
- 读帧用 OpenCV `VideoCapture.grab()` 跳帧、`retrieve()` 取样，不依赖 decord。

## D2 画面指标

- 亮度：BT.601 亮度 `Y = 0.299R + 0.587G + 0.114B`，取整帧均值 / 255，范围 0–1。
- 对比度：RMS 对比度 = `std(Y) / 255`（0–0.5）；另记 `Y` 的 p5–p95 跨度 / 255，
  对少量过曝/死黑像素不敏感，供云端参考。
- 两个量都是整帧量，不受检测结果影响；无猫时也上报（夜视/弱光判断需要）。

## D3 宠物身体来源与面积占比

接口 `PetSource.observe(frame_bgr, frame_index) -> list[PetObservation]`，
`PetObservation` = 框（分析分辨率像素）+ 可选布尔掩码 + 置信度 + 类别。

| 实现 | 面积依据 | 说明 |
|---|---|---|
| `yolo_seg`（默认） | 实例掩码 | ultralytics YOLO11n-seg，COCO `cat`(15)/`dog`(16)；构造时懒加载 |
| `track_json` | 检测框 | 读 `pet_detect_track.py` 的逐帧框（坐标按原分辨率→分析分辨率换算） |
| `none` | — | 只出画面指标，宠物相关量为 0 |

- 身体面积占比 = 所有宠物掩码并集像素 / 整帧像素；只有框时用框并集，
  载荷 `analysis.area_source` 标为 `box`（框会高估面积，云端需知道）。
- “大面积”时长：面积占比 ≥ `body_large_ratio`（默认 0.05）的累计秒数与连续段。

## D4 活动幅度

- 运动能量：相邻两个采样帧的 `|ΔY| / 255`，在宠物区域（本帧与上一帧的掩码/框并集，
  框外扩 10%）内取均值。
- 全局变化补偿：同一差分在宠物区域外的均值视为光照变化/云台转动造成的全局
  变化，`activity = max(0, 区域内均值 − 区域外均值)`。无宠物时 activity = 0。
- 位移：宠物区域质心在相邻采样点间的位移 / 画面对角线 × `analysis_fps`，
  单位“画面对角线/秒”。
- 等级：`static < 0.01 ≤ low < 0.03 ≤ medium < 0.08 ≤ high`（按运动能量），
  初值未用真实数据校准，可在 CLI 覆盖。

## D5 面部暴露

- 接口 `FaceSource.detect(frame_bgr, pet_boxes) -> list[FaceObservation]`。
- 默认 `haar`：OpenCV 自带 `haarcascade_frontalcatface_extended.xml`，CPU、
  无需下载，适合端侧；只检测正脸（= “面部朝向镜头暴露”的定义）。
  有宠物框时只在框内（外扩 10%）检测，小 ROI 放大到最短边 ≥ 160 像素再检，
  降低误检和漏检；没有宠物来源时退化为整帧检测。级联文件按
  `cv2.data.haarcascades` → 常见 conda 路径 → `--face-cascade` 顺序查找。
- 面部面积占比 = 脸框并集 / 整帧；另报“脸/身体”面积比。
- 暴露时长：检测到脸的累计秒数与连续段。
- 已知限制：Haar 对侧脸、低光、低分辨率召回较低；后续可换关键点（AP-10K 眼鼻）
  或专用猫脸检测器，接口不变。

## D6 时长与连续段

- 每个采样点有布尔状态（在场 / 大面积 / 露脸），连续 True 的采样点合并成段
  `[t_start, t_end)`；间隔 ≤ `gap_fill_sec`（默认 0.6 s）的段合并，
  短于 `min_segment_sec`（默认 0.4 s）的段丢弃，抑制单帧抖动。
- 时长 = 段长之和（合并/过滤后），与段列表一致。

## D7 行为识别信息

- 来源 A：`--actions-json`，读取 JSON 列表或 JSONL，每条至少有
  `t_start/t_end/label/score`（兼容 `scripts/live_analyze.py` 输出）。
- 来源 B：`--action-config` + `--action-checkpoint`，用 v1 七类配置
  （如 `configs/cat_action_x3d_s_v1.py`）的 `test_dataloader.dataset.pipeline`，
  以 `interval_start/interval_end` 方式在窗口（默认 4 s，步长 2 s）内采样，
  `inference_recognizer` 推理；mmaction2 懒加载，只在服务器 GPU 上运行。
- 相邻同标签窗口合并为行为段，分数取均值；`abnormal` 类与置信度低于
  `review_score`（默认 0.5）的段标 `needs_cloud_review: true`，对应需求
  “相近异常行为如无法准确区分可以标记异常和区分大类，上报到云端进一步识别”。
- 窗口汇总里附上与窗口重叠最多的行为标签。

## D8 上报载荷 `pet.highlight.v1`

顶层字段：`schema`、`event_id`（由源路径、起始时间、视频帧数、参数哈希决定，
重复运行一致）、`created_at`、`device`（`device_id`/`camera_id`）、`source`、
`analysis`（来源、阈值、代码版本）、`summary`、`segments`、`windows`（默认 1 s 窗口）、
`behavior`、`cloud_judgement`（固定 `null`，留给云端）。
字段定义见 `docs/highlight_features.md`。

## D9 亮点筛选归云端（2026-11-02 用户修订）

端侧只采集并上报上述指标与行为信息，不做亮点候选打分、筛选或裁剪；
“具体裁剪哪些作为亮点是云端的工作”。初版曾实现的端侧候选规则已删除。

## D10 本地 outbox

`--outbox <dir>` 时载荷以 `<event_id>.json` 原子写入（先写 `.tmp` 再 `os.replace`），
同名已存在则不覆盖；对应“弱网或断网时本地缓存事件”。上传器不在本 change 内实现。

## D11 运行环境

- 核心计算只依赖 numpy + OpenCV（端侧可移植）；ultralytics 与 mmaction2 都在
  实现类构造时才 import。
- 本地无 GPU，按项目规则不在本地跑模型推理；本地只运行合成数据测试。
- 服务器验证（真实猫视频、YOLO11n-seg、v1 行为模型）需先提交代码，留作后续任务。
