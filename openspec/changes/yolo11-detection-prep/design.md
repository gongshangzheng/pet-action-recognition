## Context

- 79 段 cats 视频（全部 2026-08-06、单机位、HEVC、**无音轨**）已在 pet `/home/wyy/mnt/cats/`，是 t13-1 唯一的域内数据源。
- 任务书第一阶段要求「选定候选模型」；检测链至今零实测。t13-1 原定类目为猫、人、食盆、水盆、猫砂盆、玩具、门窗；中期验收另要求上报「面部暴露面积占比」，当前类目无法支撑。
- COCO 预训练覆盖 cat/person/bowl 三类，不含猫砂盆/玩具/门窗，且未见红外成像——夜视表现必须量化而非假设。
- pet 上已有 conda env：`dlc`（DeepLabCut 3.0.1 + torch 2.8.0+cu128，已验证与驱动兼容）、mmpose 环境。ultralytics 未安装。
- 标注工具沿用 LabelStudio（project-6/8 即现有动作标注项目，团队已熟悉）。

## Goals / Non-Goals

**Goals:**

- 一条命令产出：昼夜分组的 per-class 检出统计、抽样画框视频、LabelStudio 可导入预标注包
- 类目一次性定稿（含 `cat_face`），使 9 月标注不再返工
- zero-shot 结论可追溯（原始逐帧数据落盘，改口径不需要重跑推理）

**Non-Goals:**

- 不训练/微调任何模型（t13-1 本体，9 月启动）
- 不做跟踪（BoT-SORT 属 t13-2）、不做骨架复活实验本体（只排期）
- 不建新的前端页面或 API（产物是文件，报告用 Markdown）
- 不处理音频（cats 视频无音轨，已另行升级为采集问题）

## Decisions

### D1：执行环境 — pet 新建独立 conda env `yolo`

- python 3.11 + `ultralytics`，torch 版本对齐 `dlc` env 已验证的 2.8.0+cu128。
- 备选：复用 `dlc` env —— 否决：依赖冲突风险（DLC pin 的 torch/numpy 版本），且污染已验证环境。
- 本地 Mac 不跑（无 GPU 惯例；视频在 NAS 上，本地还得重传）。

### D2：模型档位 — yolo11n + yolo11s 两档

- n 是端侧（RV1126B）部署的目标档，s 作精度参照；不跑 m+（与端侧目标无关）。
- 两档共用同一条统计管线，报告并列对比，为 t13-1 选型（n 够不够、要不要上 s）提供直接证据。

### D3：昼夜口径 — 双口径并存，原始数据落盘

- 口径 A（小时）：文件名时间戳 19:00–06:00 记为夜视候选。
- 口径 B（成像特征）：帧灰度均值 < 60 **或 HSV 饱和度均值 < 20** 记为夜视帧（阈值均可调）。
  实施中发现：该摄像头的红外夜视帧被补光灯打亮，亮度均值 ≥60，纯亮度判据会把 IR 帧误判为白天；红外帧的判别特征是**无色**（低饱和度）而非暗。
- 逐帧记录（亮度、饱和度、各类检出、conf）写入 per-video JSON，报告层再做分组——**改阈值/改口径只重算报告，不重跑推理**。

### D4：统计口径 — 帧级检出率，conf ≥ 0.25

- 「cat 检出帧率」= 该视频内 conf ≥ 0.25 存在 cat 框的帧占比（ultralytics 默认阈值）；夜视漏检率 = 1 − 夜视帧 cat 检出帧率。
- 帧级（而非框级）与下游用途对齐：事件引擎关心的是「这一帧有没有可用的猫框」。

### D5：预标注包 — 双格式导出，不引入新依赖

- 格式一：YOLO 通用格式（`images/` + `labels/*.txt` + `classes.txt`），工具链通用。
- 格式二：LabelStudio tasks JSON（`predictions.result` 用 `rectanglelabels`，坐标转 0–100 百分比），配 local storage 上传后直接预标注。不引入 `label-studio-converter`。
- 类映射：COCO `cat→cat`、`person→person`、`bowl→bowl_unspecified`（中间类，人工细分为 food_bowl/water_bowl）；`classes.txt` 写**定稿类目全集**（含 cat_face 及零样本不产出的类），保证 9 月 LabelStudio 项目一次建好。
- 帧率默认每 2s 一帧（`--frame-interval` 可调），无检出帧也导图像（空标注，供补标）。
- 备选：只导帧不带 predictions —— 保留为降级路径，见风险 R3。

### D6：类目定稿文档 — `management/docs/detection-annotation-taxonomy.md`

- wiki 形态（团队阅、可链接、随仓库走），内容：类目表（cat / person / food_bowl / water_bowl / litter_box / toy / door_window / **cat_face** / bowl_unspecified 仅预标注中间类）、每类标注边界定义、验收特征映射表（面部暴露→cat_face、身体面积占比→cat、活动幅度→cat 框时序）。
- `cat_face` 定义（草案，文档内评审定稿）：猫头部含双耳的最小外接矩形；头部不可辨认的帧跳过该类（不影响其他类）。
- tasks.json t13-1 description 改为引用本文档；骨架复活实验排期写入 progress note。

### D7：产物布局 — pet `results/detection/zeroshot_cats/`

```
results/detection/zeroshot_cats/
├── report.md / report.json          # 汇总报告（双口径分组 + n/s 对比）
├── frames/<video>.json              # 逐帧原始记录（D3 的可重算保证）
├── sampled_videos/                  # 昼夜各 4 段画框视频（seed 固定）
├── preannotation/
│   ├── yolo/{images,labels,classes.txt}
│   └── labelstudio/tasks.json
└── README.md                        # 运行参数、阈值、映射表说明
```

## Risks / Trade-offs

- **[R1] COCO 对红外夜视可能大幅漏检（训练集无红外样本）] →** 这正是本变更要量化的头号问题；若夜视 cat 检出率 < 50%，报告结论直接写明「标注必须重点覆盖夜视帧」，与预标注包的夜视帧配比挂钩。
- **[R2] 79 段全部同日单机位，结论外推受限] →** 报告显式标注该局限，结论表述限定为「该域表现」；多场景验证留给 t13-1 标注后的评测。
- **[R3] 预标注质量差会误导标注员] →** tasks JSON 中 predictions 标记来源为模型预标；若抽检发现 cat 框 IoU 明显差，降级为纯导帧（D5 备选），标注从零画。
- **[R4] ultralytics 安装/驱动冲突] →** 独立 env + torch 对齐已验证版本；失败则退 CPU 跑（79 段视频 n 档 CPU 也可接受，只是慢）。
- **[R5] 类目定稿后仍可能被验收方调整] →** 文档标注版本号与评审状态；类目全集写在 `classes.txt` 单一事实源，改动只动一处。

## Migration Plan

纯新增变更，无存量用户。回滚 = 删除脚本、产物目录与 wiki 文档；tasks.json 的 t13-1 description 改动单独一次提交，可 revert。

## Open Questions

- LabelStudio 项目的具体模板/成员分工由标注侧自定，不影响本变更产物格式。
- 若 n/s 两档差距异常（s 显著好而 n 不可用），是否补跑 m 档 —— 留给报告结论阶段决定，不动本设计。
