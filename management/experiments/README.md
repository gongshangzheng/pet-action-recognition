# 实验报告目录

每个实验主题使用独立目录，每篇报告位于该主题下的子目录：

```text
management/experiments/<topic>/<YYYYMMDD>-<runid>/
  report.md       # 报告正文（frontmatter + 固定章节）
  metrics.json    # 机器可读指标（series 折线 + tables 指标表）
  manifest.json   # 证据清单（evidence + metrics + cases + diagnostics）
  assets/         # 案例图片（随仓库提交，单图 <1MB）
```

`topic` 和报告目录名（slug）共同标识报告。不同主题可以使用相同的报告目录名。

## report.md

frontmatter 必填：`title`、`date`、`run_id`、`status`、`verdict`、`summary`、`source`；可选：`change`（关联的 openspec change）。

- `status` 取 `complete` / `partial` / `failed`（**执行状态**：这次 run 跑完了没有）
- `verdict` 取 `improved` / `no-gain` / `worse` / `inconclusive`（**结论方向**：干预有没有效）
- 两者独立：失败的 run 也可以有完整的报告（如实记录为什么失败）。
- `source` 指向该报告依据的 run 产物路径（仓库相对路径，如 `evaluation/results/xxx.json`）。

正文包含八个固定章节（缺章节 → 报告标记 incomplete）：

```markdown
## 结论摘要
## 实验问题与假设
## 实验设置与环境
## 指标结果
## 案例展示
## 失败案例与限制
## 结论与建议
## 产物来源
```

标题使用「实验主题：对照方案与评估目标」格式，说明对象和比较内容，不预设结论。

环境段（「实验设置与环境」）按行内清单记录（缺项 → incomplete，不虚构）：模型（id + 版本/端点）、数据集（id + 版本/规模）、配置、运行时间戳、执行入口（脚本/命令）、随机种子（若有）。例如：

```markdown
- 模型: gpt-4 / v2 (https://api.openai.com/v1)
- 数据集: mmlu-subset / 500 题
- 配置: eval-quick
- 运行时间戳: 2026-11-02T10:00:00
- 执行入口: python3 .agents/skills/evaluation/scripts/run_evaluation.py eval-quick
- 随机种子: 42
```

## metrics.json

```json
{
  "series": [{ "name": "系列名", "x_label": "x 轴", "y_label": "y 轴", "points": [{ "x": 1, "y": 0.5 }] }],
  "tables": [{ "title": "表名", "columns": ["列1", "列2"], "rows": [["a", "1"]] }]
}
```

`series` 渲染为折线图，`tables` 渲染为指标表。指标须注明单位、样本量与局限（局限写进 manifest 的 metrics 条目）。

## manifest.json

三个必填部分 + 一个推导部分：

- `evidence`（六项，缺任一 → incomplete）：实验类型 / baseline 数值来源 / 可辨识性 / 样本量 / 失败边界 / 结论上界
- `metrics`：每条含 `name`、`unit`、`baseline`、`result`、`delta`、`sample_size`、`source`、`limitation`（不可比较时写明原因）
- `cases`：每条含 `id`、`kind`（目前仅 `image`）、`src`（`assets/<file>`）、`source_run`、`input`、`selection_reason`、`sha256`。**案例必须由作者显式选择**，生成器不自动把扫描到的文件当作代表性案例
- `diagnostics`（生成器写入）：缺失项清单，报告 incomplete 的原因

## incomplete 语义

报告完整度不由作者自评，由生成脚本与后端按同一规则推导：frontmatter 必填齐全、八章俱全、evidence 六项齐全、每条 metric 八字段齐全、每个 case 的图片存在且 sha256 匹配。任一不满足 → incomplete；页面明确显示缺失原因，不假装可审阅。

## 生成报告

用 `.agents/skills/experiment/scripts/build_report.py`（纯标准库），作者清单驱动：

```bash
python3 .agents/skills/experiment/scripts/build_report.py \
  --topic <topic> --slug <YYYYMMDD>-<runid> --date <YYYY-MM-DD> \
  --run-id <run-id> --status complete --verdict inconclusive \
  --title '实验主题：对照方案与评估目标' \
  --source evaluation/results/<x>.json \
  --manifest report-input.json          # report 文字 / evidence / metrics / cases
```

作者清单（`--manifest` 输入）示例见 `build_report.py` docstring。脚本不覆盖已有报告（`--force` 显式覆盖）。方法论（何时该写报告、证据标准、样本量门槛）见 `.agents/skills/experiment/SKILL.md`。
