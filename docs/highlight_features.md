# 亮点抓取特征与云端上报载荷（`pet.highlight.v1`）

更新日期：2026-11-02。对应 OpenSpec change：`extract-highlight-features`。
对应需求：`项目要求.txt` 中期验收第 2 条“亮点抓取（提取出画面亮度，对比度，
宠物活动幅度，宠物身体画面中面积占比和时长，面部暴露面积占比和时长，及行为识别
信息上报到云端进行判断）”。

**状态**：代码与合成数据单元测试完成（15 项通过，Python 3.8 / 3.11）；已在本机对 8 段
单猫真实视频跑通 YOLO11n-seg + Haar（见“本机示例”）；行为模型路径未运行；所有阈值都是
初值、未校准。云端接收与判断不在本次范围，载荷只写本地文件 / outbox。

## 用法

```bash
# 服务器（GPU）：YOLO11n-seg 身体掩码 + Haar 猫脸 + v1 七类行为模型滑窗
python scripts/extract_highlight_features.py \
    --video datasets/cat_raw/videos/<name>.mp4 \
    --pet-source yolo_seg --yolo-weights checkpoints/ultralytics/yolo11n-seg.pt --device cuda:0 \
    --action-config configs/cat_action_x3d_s_v1.py \
    --action-checkpoint results/training/cat_action_v1/x3d_s/work/best_macro_f1_epoch_20.pth \
    --camera-id cam-01 --start-time 2026-11-02T10:00:00+08:00 \
    --out results/highlights/<name>.json --outbox results/highlights/outbox

# 已有检测轨迹 / 已有行为时间轴
python scripts/extract_highlight_features.py --video x.mp4 \
    --pet-source track_json --track-json results/.../track.json \
    --actions-json results/.../timeline.jsonl --out results/highlights/x.json

# 只算画面指标（无模型依赖）
python scripts/extract_highlight_features.py --video x.mp4 --pet-source none --face none --out x.json

# 单元测试（合成数据，本地可跑）
python scripts/test_highlight_features.py -v

# 人工核对：把载荷（需 --include-samples）画回视频 + 拼图
python scripts/render_highlight_demo.py --payload results/highlights/x.json --out results/highlights/x_vis
```

代码位置：`petlib/highlights/`（`metrics` 计算、`sources` 宠物/面部来源、`actions` 行为时间轴、
`aggregate` 汇总、`report` 载荷与 outbox），CLI 为 `scripts/extract_highlight_features.py`。

## 处理流程

1. 按 `--analysis-fps`（默认 5）跳帧采样，缩放到 `--analysis-width`（默认 960）。
   15 fps 原视频即每 3 帧取 1 帧，每个采样点代表 0.2 s。
2. 每个采样点计算画面指标；宠物来源给出身体掩码/框；面部来源在宠物框内找正脸；
   与上一采样点比较得活动幅度。
3. 逐采样点布尔状态（在场 / 大面积 / 露脸）合并为连续段并累计时长。
4. 按 `--window-sec`（默认 1 s）汇总窗口，挂上重叠最多的行为段。

**端侧只采集并上报指标，不挑选、不裁剪亮点片段**——哪些片段算亮点由云端判断。

## 指标定义

| 指标 | 定义 | 单位 / 范围 |
|---|---|---|
| 亮度 `brightness` | BT.601 亮度 `0.299R+0.587G+0.114B` 的整帧均值 / 255 | 0–1 |
| 对比度 `contrast_rms` | 亮度标准差 / 255（RMS 对比度） | 0–0.5 |
| 对比度 `contrast_spread` | 亮度 p95 − p5，/ 255；不受少量过曝/死黑像素影响 | 0–1 |
| 活动幅度 `activity` | 相邻采样帧 \|ΔY\|/255 在宠物区域（本帧+上一帧掩码/框并集，框外扩 10%）内的均值，减去区域外均值（光照变化、云台转动等全局变化），下限 0 | 0–1，常见 < 0.2 |
| 活动等级 | `static < 0.01 ≤ low < 0.03 ≤ medium < 0.08 ≤ high`（按窗口内活动均值） | 枚举 |
| 位移 `displacement` | 宠物区域质心在相邻采样点间的位移 / 画面对角线 / 时间 | 画面对角线 / 秒 |
| 身体面积占比 `body_area_ratio` | 所有宠物掩码并集（无掩码时为框并集）像素 / 整帧 | 0–1 |
| 大面积时长 `body_large_sec` | 身体面积占比 ≥ `--body-large-ratio`（默认 0.05）的累计时长 | 秒 |
| 在场时长 `pet_visible_sec` | 检出至少一只宠物的累计时长 | 秒 |
| 面部面积占比 `face_area_ratio` | 检出的正脸框并集 / 整帧 | 0–1 |
| 脸/身体比 `face_body_ratio` | 面部面积 / 身体面积 | 比值 |
| 露脸时长 `face_exposed_sec` | 检出正脸的累计时长 | 秒 |

时长统一来自连续段：间隔 ≤ 0.6 s 的段合并，短于 0.4 s 的段丢弃（`--gap-fill-sec` /
`--min-segment-sec`），所以时长与段列表一致，不是采样点简单计数。

## 来源

| 选项 | 说明 |
|---|---|
| `--pet-source yolo_seg`（默认） | ultralytics YOLO 实例分割，只保留 COCO cat/dog；需本地权重文件，**不自动下载**；面积按掩码计 |
| `--pet-source track_json` | 读 `scripts/pet_detect_track.py` 的 `track.json`（`smooth_track[].box`）；面积按框计，会高估 |
| `--pet-source none` | 不检测宠物，宠物相关量为 0 |
| `--face haar`（默认） | OpenCV 自带 `haarcascade_frontalcatface_extended.xml`；CPU、无需下载；只在宠物框内（外扩 10%，小框放大到最短边 160 px）检测正脸 |
| `--face none` | 不检测面部 |
| `--actions-json` | 已有行为时间轴（JSON 列表、`{"segments": [...]}` 或 JSONL；字段 `t_start/t_end/label/score`，可带 `top5`/`top_k`，兼容 `live_analyze.py` 输出） |
| `--action-config` + `--action-checkpoint` | MMAction2 区间模型滑窗推理（默认 4 s 窗口、2 s 步长），使用配置里 test_dataloader 的 pipeline；每个窗口负责以窗口中心划分的不重叠时段 |

`analysis.area_source` 标明面积来自 `mask`、`box` 还是 `none`。

## 载荷结构

```jsonc
{
  "schema": "pet.highlight.v1",
  "event_id": "hl-<20 位十六进制>",     // 源路径、起始时间、帧数、参数、来源决定；重复运行一致
  "created_at": "2026-11-02T02:00:00+00:00",
  "device": {"device_id": "...", "camera_id": "..."},
  "source": {"video", "file_name", "fps", "frames", "width", "height", "duration_sec", "start_time"},
  "analysis": {"analysis_fps", "sample_step", "analysis_size", "area_source",
               "pet": {...}, "face": {...}, "behavior": {...}, "review_score",
               "config": {...全部阈值...}, "thresholds_calibrated": false,
               "code": {"git_head", "highlights_dirty"}},
  "summary": {
    "duration_sec", "samples",
    "brightness" / "contrast_rms" / "contrast_spread": {"mean","min","p50","max"},
    "pet_visible_sec", "pet_visible_ratio", "max_pets",
    "body_area_ratio": {...在场时统计...}, "body_large_sec",
    "activity": {...在场时统计...}, "displacement": {...}, "activity_level_sec": {"static","low","medium","high"},
    "face_exposed_sec", "face_exposed_ratio_of_visible", "face_area_ratio": {...}, "face_body_ratio": {...}
  },
  "segments": {"pet_visible": [[t0, t1], ...], "body_large": [...], "face_exposed": [...]},
  "windows": [{"t_start","t_end","samples","brightness","contrast_rms","contrast_spread",
               "pet_present_ratio","max_pets","body_area_ratio_mean","body_area_ratio_max",
               "activity_mean","activity_max","activity_level","face_exposed_ratio",
               "face_area_ratio_max","action": {"label","score","needs_cloud_review"} | null}],
  "behavior": {"source": "mmaction2_window" | "timeline_json" | "none",
               "segments": [{"t_start","t_end","label","score","top_k","n_windows",
                             "needs_cloud_review","review_reasons"}],
               "needs_cloud_review": true},
  "cloud_judgement": null,               // 留给云端
  "samples": [...]                       // 仅 --include-samples
}
```

- 时间都是相对片段开头的秒数；绝对时间 = `source.start_time` + 秒数。
- 行为段 `needs_cloud_review`：类别为 `abnormal`（`abnormal_class`）或平均分低于
  `--review-score`（默认 0.5，`low_confidence`）。对应需求“相近异常行为如无法准确区分
  可以标记异常和区分大类，上报到云端进一步识别”。

## 本机示例（2026-11-02，RTX 3060 Laptop，单猫视频）

环境：临时 venv（继承 `reid` 环境 torch 2.4.1+cu121，新装 ultralytics 8.3.40），
`yolo11n-seg.pt` 从 4090 复制（SHA-256 `55ed65c5…`）。产物在 `results/highlights/demo/`
（gitignored）。速度：40 s 视频约 21 s、15 s 视频约 12 s（含模型加载，5 fps 采样）。

| 视频 | 时长 | 在场 | 身体占比均值 | 活动均值 | 露脸 | 人工核对 |
|---|---:|---:|---:|---:|---:|---|
| chmtg0l 0703_125003（黑白画面，走动） | 40.3 s | 40.3 s | 0.039 | 0.026 | 0 s | 全程框住；侧身/背对，无正脸，0 正确 |
| chxnpw3 0620_092615（进食） | 15.1 s | 12.1 s | 0.018 | 0.026 | 0 s | 背对镜头无正脸；蜷身时 YOLO 漏检 3 段（t≈5–7、11 s） |
| chxnpw3 0503_161345 | 15.1 s | 6.9 s | 0.016 | 0.025 | 0.6 s | 5 次猫脸命中全部是真正脸（约 25 px 小脸也检出） |
| chmtg0l 0730_095845（黑白画面） | 34.0 s | 30.8 s | 0.035 | 0.028 | 0.8 s | 5 次猫脸命中全部是误检：椅子黑色金属腿压在蓬松猫毛上 |

四段亮度均值 0.45–0.49、RMS 对比度 0.25–0.27；其余字段见各载荷 JSON。

结论与问题：
- 画面亮度/对比度、身体面积、活动幅度在单猫视频上数值合理，框与画面一致。
- **YOLO11n 零样本在蜷身、背对时会漏检**，与 `yolo11-detection-prep` 结论一致（召回代理
  约 48.5%）；端侧需要域内微调的 YOLO11n。
- **Haar 正脸检测：真脸能检出，但黑白画面里有结构性误检**。把 `minNeighbors` 从 3 调到
  5 / 7，误检 5→3→1，真脸 5→4→2，无法干净分开；样本太少，暂保持默认 3，待更多正负样本再定。
- 抽样筛选时 `chmtg0l`、`chxnpw3` 个别视频也出现过 2 个框，是否真有第二只猫未逐一核对。

## 本地 outbox

`--outbox <dir>` 时以 `<event_id>.json` 原子写入（先写临时文件再重命名），同名已存在
则不覆盖，对应“弱网或断网时本地缓存事件”。本次没有实现上传器，也没有实现清理策略。

## 已知限制与待办

- **未在真实视频上验证**：按项目规则，服务器执行前须先提交代码；用户要求暂不提交，
  所以真实猫视频、YOLO11n-seg、v1 行为模型的联调待提交后进行。
- 阈值（活动等级、大面积）均为初值，需按真实分布回调。
- Haar 正脸级联对侧脸、低光/红外、远距离小脸召回偏低；接口可换成关键点（AP-10K 眼鼻）
  或专用猫脸检测器。
- 活动幅度基于帧差，云台转动时用区域外变化补偿，但强烈的局部光照变化（开灯照到猫）
  仍会计入。
- `track_json` 只有单猫框；多猫时面积和活动是所有宠物的并集，不区分个体。
- 端侧（RV1126B）部署时，画面指标与 Haar 都可直接移植；YOLO 分割和行为模型需另行
  转换为 RKNN，不在本次范围。
