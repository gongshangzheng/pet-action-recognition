# speedrun-run-name Design

## Context

见 proposal.md - Why。现状：`results/speedrun/results.json` 每条记录含 `id / model_id / video / checkpoint / gt_label / correct / metrics / output_video / status / rtf / gpu_mem_mb / finished_at`，无批次标识。前端 SpeedRun.vue 筛选器仅 model_id + video。后端 `server/routers/speedrun.py` 的 `/results` 直接返回全量。

## Goals / Non-Goals

**Goals**
- 结果记录增加 `run_name`，新执行必须携带
- API 支持 `?run_name=` 过滤
- 前端批次筛选器 + 统计联动
- 历史数据零迁移成本（读取侧缺省 `legacy`）

**Non-Goals**
- 不回写/迁移历史 JSON 文件
- 不改 speedrun 执行核心逻辑（推理流程不变）
- 不做批次管理 CRUD 页面（重命名/删除批次等）

## Decisions

### D1: 字段名 `run_name`，读取侧兼容而非数据迁移
- 读取 `results.json` 时，缺 `run_name` 的记录在内存中补 `run_name="legacy"`，不回写磁盘
- 理由：303+ 条历史记录分布在本地与 pet 两份文件，回写有损坏风险；读取侧兼容零风险
- 备选：一次性迁移脚本回写 → 拒绝，无收益且引入写入风险

### D2: run_name 来源——执行时传入，缺省自动生成
- `/api/speedrun/run` 请求体接受可选 `run_name`；未传时自动生成 `{dataset}-{YYYYMMDD-HHmm}` 格式
- 批量脚本（如 speedrun_cats.py）在写结果时显式传入，如 `cats-v1-speedrun`
- 理由：显式传入保证语义化命名；自动生成兜底防遗漏

### D3: 前端筛选器从结果集动态生成
- `runNameOptions = [...new Set(results.map(r => r.run_name))]`，与现有 modelOptions/videoOptions 同模式
- 不新增「批次列表」API，避免过度设计
- 统计 computed（accuracy/rtf/mem）基于 filteredResults，已有模式直接复用

### D4: 已跑完的 cats 批次补标 run_name
- 对 pet 上现有 303 条 cats 结果（id 前缀 `speedrun-{model}-event_2026*`，video 路径含 `quadruped_cats_v1`）执行一次性补标脚本，写 `run_name="cats-v1-speedrun"` 并同步回本地
- 理由：这是本变更的动机数据，不补标则它们落入 legacy，用户仍无法区分
- 本地与 pet 的 results.json 都更新（本地优先，rsync 到 pet）

## Risks / Trade-offs

- [旧前端缓存 JS 不带新筛选器] → vite dev 热更新即可；强缓存时硬刷新
- [run_name 自由文本导致命名散乱] → design 给出命名约定 `{数据集}-{用途}-{日期}`，文档提示
- [pet 与本地 results.json 漂移] → 补标后以 pet 为准 rsync 回本地（pet 是执行端）

## Migration Plan

1. 改后端 + 前端 + 脚本
2. 跑一次性补标脚本（pet）
3. rsync results.json 回本地
4. 重启 pet 后端（`restart_services.sh`），本地硬刷新验证

回滚：代码回滚即可；`run_name` 字段对旧代码无害（旧读取逻辑忽略未知字段）。
