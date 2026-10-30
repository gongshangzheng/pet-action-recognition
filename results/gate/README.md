# results/gate/ 目录规范（门控 presence-gate-model）

> 目标：任何人（包括未来的我）打开这个目录就能回答三件事——**这批数字是哪份数据、哪个模型、哪条命令产出的**。
> 一句话原则：**一个 run 一个目录，结论进 evidence，一次性探针进 probes，日志进 logs。**

## 目标结构（v2 规范，新产物按此落盘）

```
results/gate/
├── dataset/<version>/           # 数据集快照
│   ├── frames/<date>/*.jpg      #   整帧（长边 1280，q90）
│   ├── manifest.csv             #   每帧一行（path/video/date/group/domain/split/frame_idx/sat/luma）
│   ├── splits_by_date.json      #   日期 → split（可复现）
│   ├── sample_stats.json        #   抽样与解码统计（含失败清单）
│   └── dataset_card.md          #   规模/分布/偏差/口径
├── labels/<stage>-<config>/     # 标注产物（教师或学生）
│   └── *.jsonl                  #   每帧一行：path/label/scores/box/teacher/tiles/threshold
│       binary-<ver>.jsonl       #   二态折叠（present/absent，原三态留在 audit_label）
├── runs/<run-id>/               # 训练/评测，一个 run 一个目录
│   ├── best.pt                  #   权重
│   ├── threshold.json           #   冻结阈值 + val 上反解依据
│   ├── metrics.json             #   按域（day/night）× split 的 recall/FPR/precision
│   ├── predictions_<split>.jsonl#   逐帧预测（概率 + 真值 + 域）
│   └── env.json                 #   commit/env/库版本/GPU/seed（env_check.sh 产出）
├── review/<set>/                # 人工核验集
│   ├── items.json               #   教师判定 + 框 + 场景标签
│   ├── frames/...               #   帧副本（可整体搬到本机标注）
│   └── labels.csv               #   人工标注（present/absent/uncertain）
├── probes/<name>-<YYYYMMDD>.json# 一次性探针报告（motion / latency / 判别力…）
├── contact_sheets/<set>/*.jpg   # 给人看的接触表（可随时重建，不入库）
└── logs/<YYYYMMDD>-<task>.log   # 运行日志（stdout 已足够时可不留）
```

- `<run-id>` / `<version>` 用 `小写短描述-YYYYMMDD[轮次字母]`，禁止 `test2` / `final` / `new`。
- **失败/中断的 run 也留目录**，在 `metrics.json` 里写 `execution_status`（完成/部分完成/失败），不删。
- 判定依据（阈值、分母、样本量）必须落在对应 run 的 `threshold.json` / `env.json`，不要只写在对话里。

## 当前实际内容（v1，2026-10-30 盘点）

| 路径 | 是什么 | 归属新结构 |
|---|---|---|
| `dataset_v1/` | 600 段 → 15,139 帧（2.7 GB），日期划分、昼夜打标 | → `dataset/v1/` |
| `pilot_v1/` | 20 段试跑（验证管线） | 可删 |
| `labels_yolo.jsonl`、`labels_yolo640_merged.jsonl` | YOLO@640 教师（**已被 GDINO 取代**，仅作对照） | → `labels/yolo-640/` |
| `labels_native_t1/t2*.jsonl`、`labels_native_full_t3.jsonl`、`labels_native_remaining_t*.jsonl` | GDINO 原生分辨率标注（tiles=1/2/3 各档） | → `labels/gdino-native-<tiles>/` |
| `labels_native_all_t3.jsonl` | **当前权威三态标签**（15,139 帧，阈值 0.15） | → `labels/gdino-native-3/` |
| `labels_binary.jsonl` | 二态折叠（present 97.5% / absent 2.5%） | → `labels/gdino-native-3/binary-v1.jsonl` |
| `labels_native_final.jsonl` | dog 放大复核的产物；**当前缺失**（任务被守卫/断连打断） | 待重跑 |
| `runs/mnv3s_448_bin/` | **当前唯一有意义的模型 run**（MobileNetV3-S 1.52 M，448 输入） | → `runs/gate-mnv3s-448-20261030a/` |
| `runs/smoke_mnv3*` | 700 帧冒烟（错标签，仅验证链路） | 可删 |
| `subset_400.csv`、`subset_hard60.csv`、`smoke_manifest.csv`、`manifest_remaining.csv` | 抽样清单（探针输入） | → `probes/` 或就地保留 |
| `motion_probe.json`、`motion_windowed.json`、`latency_gpu.json`、`latency_cpu.json`、`env_check.json` | 探针/基准报告 | → `probes/` |
| `review/set1/`（240 帧）、`review3_*/`、`review/` | 人工核验集与接触表 | → `review/set1/`、`contact_sheets/` |
| `*.log`、`gpu_watch.jsonl`、`GPU_FREE`、`launch.log` | 运行日志（含隧道抖动期间的轮询记录） | → `logs/` |
| `.run/guard/*.log`（仓库根下） | 资源守卫采样（5 s 一条，含 CPU/RSS/显存） | 保留原位（remote-ops 约定） |

**本机（mac）副本**：`results/gate_review/`、`results/gate_review3/`（接触表）、`results/gate/review/set1/`（核验集，供网页标注）。
本机与远端的一致性：帧与标签以**远端为准**，本机只放"给人看"的产物与核验集副本。

## 纪律

1. **只写自己的目录**：新产物先想好落 `dataset|labels|runs|review|probes|logs` 哪一类，不往根目录扔文件。
2. **结论不进 results**：`results/` 被 gitignore，任何要长期保留的结论必须写进
   `openspec/changes/presence-gate-model/evidence.md`（数字 + 出处 + 上界）。
3. **可复用脚本不入 results**：进 `scripts/` 或 `.claude/skills/<skill>/scripts/` 并提交；一次性探针放 `tmp/`。
4. **每次训练/评测留 env.json**：`env_check.sh --json <run>/env.json`，否则那批数字不可复现。
