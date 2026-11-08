# 设计与验证

## 配色映射（slate → 令牌）

| 原值 | 用途 | 令牌 |
|---|---|---|
| `#1e293b` | 论文标题、中英摘要正文 | `--color-text-heading` |
| `#334155` | 概述正文 | `--color-text` |
| `#475569` / `#64748b` | 摘要、作者、统计标签 | `--color-text-secondary` |
| `#94a3b8` | 英文标题、日期、占位说明 | `--color-text-dim` |
| `#fff` | 卡片面、详情浮窗面 | `--color-card` |
| `#f8fafc` / `#f1f5f9` | 统计栏、缩略图底、悬停底 | `--color-elevated` / `--color-hover` |
| `#e2e8f0` | 边框、分隔线 | `--color-border` |
| `rgba(0,0,0,0.08)` | 卡片阴影 | `--color-shadow` |
| `#f59e0b`（来源标签） | Blog 标签文字 | `--tag-medium-fg` + `--tag-medium-bg` |

## 同时修掉的三处结构问题

- 钉住态的 `border-left: 3px` 色条：超 1px 的彩色左边框，靠 `--color-primary-soft` 底色 + 置顶按钮表达状态。
- 论文条目同时带「边框 + 白底 + 阴影」，又嵌在页面 `n-card` 里 → 改成 `--color-elevated` 内嵌表面（与数据集卡、SpeedRun 视频卡同一处理）。
- emoji 当图标（📝/✨/📌/⭐）：换成 `@vicons/ionicons5` 的 `CreateOutline / SparklesOutline / PinOutline / StarOutline / Star`；`type="info"` 实底按钮（白字 3.9:1）改走主色。

## 验证（临时插入 1 条本地 demo 记录后实测，测完删除）

| 检查 | 修复前 | 修复后 |
|---|---|---|
| 浅色对比度失败（列表 + 详情浮窗） | 6 + 2 | 0 |
| 深色对比度失败 | 11 + 2 | 0 |
| detector（列表页，含渲染出的卡片） | nested-cards + flat-type-hierarchy | 0 |

层级调整为 20 / 16 / 14 / 12（页面标题 / 论文标题 / 正文 / 元信息）；390px 下卡片宽 260px、无横向溢出。

`data/papers.db` 已恢复原状（0 行），临时数据未入库。
