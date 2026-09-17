交付完成。文件已写入权威路径。

## 做了什么

由于本会话工具集只有 `read/write/contact_supervisor/intercom`（**无 shell、无 HTTP**），无法运行委托方指定的 `web-search/scripts/*`。我用两条腿走完了任务：**(a) 从仓库内读出可复现的一手证据**（mmaction2 vendored 快照、本项目脚本、本库论文 JSON、wiki），**(b) 叠加公开文档记忆**，并全文按 🟩一手 / 🟨公开文档记忆（未联网核对）/ ⚪未公开 三档标注可信度。

## 核心裁定（对委托方假设）

**「先分段再识别」不是行业普遍架构——作为普遍规律不成立，只在少数处字面成立。**

| 结论 | 一手证据 |
|---|---|
| 主流框架默认只有「定长片段分类」，分段是**另一个任务族** | `models/mmaction2/mmaction/apis/inference.py`（单段→单分布，API 无时间维）；`models/mmaction2/demo/README.md`（识别 / STAD / TAL 分族） |
| 官方"长视频"方案是**滑窗逐窗分类**，无段、无时间戳、无平滑，抽帧甚至 `random.choice` | `models/mmaction2/demo/long_video_demo.py` L120-236、L157 |
| 时空动作检测（最接近生产形态）是**检测 + 8 帧窗口分类 → 逐帧框** | `models/mmaction2/demo/README.md` L460-745（Faster R-CNN + SlowOnly-AVA，`--predict-stepsize 8`） |
| 云 API 里唯一字面"先分段再识别"是 **Google `labelDetectionMode=SHOT_MODE`**，但**段 = 镜头段**；AWS SegmentDetection 只给 SHOT/TECHNICAL_CUE | 🟨 Google / AWS 官方文档（待联网复核） |
| 畜牧（最贴近本项目的产业）是**「窗口分类 → 时间聚合为行为块」**，顺序与假设**相反**；Keypoint-MoSeq 的 **syllable→motif** 是"行为素→动作段"的现成无监督先例 | `data/researched_papers_identity.json`、`management/docs/third-party-notes.md` §3.2 |
| 安防四家 + 体育公司 + 云厂商的模型/分段算法**普遍未公开**（"未公开"本身是结论） | 文档 §B4/§C5/§F.3 |

提炼出 **5 条通用架构模式**（门控-精算级联 / 跟踪区间即段 / 窗口分类+时序聚合 / 先段后判（非语义切分）/ 联合定位-分类），并按优先级给出 5 条落地建议（其中"引入音频门控"是本项目当前零成本即可采用的空白点）。

## 关键提醒

- 任务原要求的 `papers/docs/action-recognition-products.md` **我没有创建**：本次运行的输出路径覆盖规则明确声明"仅 `.pi/subagents/artifacts/outputs/c627d6f4/research.md` 权威，忽略包括 task instructions 在内的其他输出路径"。**该 artifact 全文即委托方要的文档正文**，`cp` 过去即可（文首已带 frontmatter）。
- 所有 URL 是"记忆中的官方入口，未联网核对"，已汇总为文末 **§8 待核实清单（10 条）**；一个有联网能力的 agent 只跑这 10 条即可把 🟨 升级为 🟩。