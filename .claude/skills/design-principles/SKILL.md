---
name: design-principles
description: |
  UI/UX 设计原则与公约。用于新建页面、列表页、结果展示、轮询、可视化等场景时遵循统一的设计规范。
  触发场景：(1) 创建新的列表/结果页，(2) 设计分页逻辑，(3) 选择组件布局方案，(4) review UI 改动，(5) 实时轮询/曲线，(6) 封面图/缩略图，(7) 卡片布局
---

# UI/UX 设计原则

本 skill 记录 ProjFlow 项目的设计公约，确保不同页面、不同开发者产出的 UI 风格一致。

## 1. 列表/结果页必须分页

**原则**：当页面列出多项结果（论文、图片、视频、任务、成员等）时，**必须分页**，不要一次渲染全部。

**为什么**：
- 数据量不确定（可能几十条也可能几百条），全量渲染会导致页面卡顿。
- 用户浏览习惯是一页一页翻，不是一次性看全部。
- 分页让前端组件保持响应性，避免大数据量下 DOM 节点过多。

**后端 API 格式**：
```
GET /api/xxx?offset=0&limit=50
→ { "total": N, "offset": 0, "limit": 50, "items": [...] }
```
- 用 `offset/limit` 而非 `page/page_size`（offset 对前端更直观，避免页码计算）。
- 返回 `total` 让前端知道总页数，返回 `offset/limit` 回显当前页。

**前端分页策略（按页面类型选）**：

| 页面类型 | 策略 | 组件 | page_size |
|---------|------|------|-----------|
| 数据表格 | 远程分页 + 页码器 | `<n-data-table>` remote 模式 + `<n-pagination>` | 50 |
| 卡片/图片网格 | "加载更多"按钮 | 前端追加 + 按钮触发 fetch | 12–24 |
| 详情内嵌列表 | 懒加载 + "加载更多" | 初始渲染 N 条，按钮扩展 | 12 |
| 输出文件/日志 | 远程分页 + 页码器 | `<n-pagination>` | 100 |

**重字段剥离**：列表 API 不返回详情页才需要的重字段。例如：
- 评测结果列表：返回摘要（id、model、dataset、status、metrics），不返回完整 `outputs` 数组。
- 训练运行列表：返回 `id、title、status`，不返回 `test_metrics` 和 `viz`（图片 base64）。
- 详情页单独请求完整数据。

**轮询优化**：
- 只在有"进行中"任务时才启动轮询（如训练运行、评测执行）。
- 轮询时只 fetch 当前页，不要每次重新拉全量。
- 任务全部完成后停止轮询。
- 训练曲线轮询：详情页 `getTrainRunDetail(runId)` 3s 轮询；后端 status=running 时实时读 `work_dir/vis_data/scalars.json` 补 `loss_series`，训练中曲线随 epoch 增长。
- 可视化样本轮询：同一轮询周期内 `listVisSamples(runId)` 拉取最新 epoch 分组卡片，新 epoch 完成后卡片自动出现。
- 进程列表页轮询：`getTrainRuns()` 3s 轮询，只刷当前页数据；全部进程结束后停轮询 + 补刷一次。

**缓存**：
- 后端：对频繁读取的文件（results.json、metrics.json）加 mtime-aware TTL 缓存，文件没变就不重新解析。
- 前端：列表页用 `keep-alive` 或本地缓存，切换回来时不重新 fetch（除非用户主动刷新）。
- **keep-alive 现状**（`MainLayout.vue`）：缓存 `PaperList / TrainResults / DatasetBrowser / ReportPage` 四个重列表页（组件需 `defineOptions({ name })` 与 include 列表一致）。被缓存的轮询页必须 `onDeactivated` 停轮询、`onActivated` 恢复（参考 TrainResults）；PaperList 的滚动监听同样在 deactivated/activated 摘下/挂回。
- **轮询 diff**：所有定时轮询（TrainResults / TrainRunDetail / SpeedRun）先 `JSON.stringify` 对比快照，数据没变就跳过响应式赋值，避免表格/图表每 3s 全量重渲染。

**例外**：
- 数据量固定且很小（< 10 条），如里程碑列表、项目树根节点。
- 树形结构天然有折叠/展开，不需要分页（如项目树）。

## 2. 状态色统一

项目内所有"状态"用同一套颜色：
- 进行中/active → 绿色（`#22c55e`）
- 待开始/planned → 蓝色（`#3b82f6`）
- 已完成/completed → 灰色（`#71717a`）
- 暂停/paused → 黄色（`#eab308`）
- 阻塞/blocked → 红色（`#ef4444`）

状态用圆点（`.status-dot`）+ 文字标签展示，不要用彩色大色块（太刺眼）。

## 3. 空状态不报错

数据为空时展示友好的空状态图标 + 一句话说明，不要用空白页或报错提示。

```vue
<div class="empty">
  <n-icon size="32" color="#52525b"><icon-name /></n-icon>
  <p>暂无 XXX 数据。</p>
</div>
```

## 4. 悬浮卡 vs 详情页

- **悬浮卡**（hover-card）：轻量预览，鼠标悬停触发，展示关键字段（3-5 个）。
- **详情页**：完整信息，点击后进入，可包含笔记、进展记录、附件等。

判断标准：如果信息超过 5 个字段或需要滚动，就做详情页，不要堆在悬浮卡里。

## 5. 表单验证

- 必填字段用 `*` 标注，提交时前端先验证再发请求。
- 错误提示贴在输入框下方，不要用全局 toast（toast 留给成功/系统级错误）。
- 用 Naive UI 的 `n-form` + `rules` 做表单校验。

## 6. 响应式断点

目前只做了桌面端（最小宽度 1024px）。如果将来做移动端，断点定在 900px：
- `≥ 900px`：双列/三列网格、侧边栏常驻。
- `< 900px`：单列、侧边栏抽屉。

## 7. 加载状态

- 短请求（< 500ms）：不显示加载态，避免闪烁。
- 长请求（> 500ms）：展示骨架屏或 `加载中…` 文字，不要空白等待。
- 用 `v-if="loading"` 控制加载态，不要用 `:disabled` 按钮（用户不知道在等什么）。

## 8. 错误处理

- 网络错误 / API 500：全局 toast 提示"网络异常，请稍后重试"。
- 业务错误（如"论文不存在"）：在页面内展示错误卡片，不要用 alert。
- 不要在控制台打印敏感信息（API key、用户数据）。

## 9. 加载性能

页面必须**加载快速**，用户不应感到明显等待。

**首屏优化**：
- 路由懒加载：`const Comp = () => import('./views/xxx.vue')`，不要把整个页面组件提前 import。
- 图片懒加载：`<img loading="lazy" />`，或用 Intersection Observer 做视口内才加载。
- 骨架屏优先：先渲染骨架占位（`<n-skeleton>`），数据到了再替换，避免白屏。

**列表页性能**：
- 分页是基本手段（见 §1），不要一次加载几百条。
- 如果数据量极大且需要无限滚动，用虚拟滚动（`<n-virtual-list>`），不要渲染所有 DOM 节点。
- 搜索/筛选走后端，不要前端全量 fetch 再 filter（数据量大时卡死）。

**图片/媒体资源**：
- 缩略图用压缩版（< 100KB/张），原图只在详情页加载。
- 视频封面用 `<video preload="metadata">` 只加载首帧，不要 `preload="auto"` 预载整个视频。
- 大图（> 1MB）加 loading 提示或骨架屏，不要让用户看着空白区域猜。
- **视频封面图（cover）**：视频文件用中间帧 JPG 作封面（`_extract_cover` / `_annotate_video_cv2`），`<img loading="lazy">` 展示；点击才加载视频（`<video preload="none">` 或 VideoModal）。同一视频的封面图跨模型复用（`results/speedrun/covers/<video_stem>.jpg`）。
- **数据集浏览器封面**：`GET /api/datasets/{id}/thumb?path=video.avi` 按需提取中间帧 + 缓存到 `datasets/.thumbs/`，后续请求直接返回缓存 JPG。

**卡片/网格布局**：
- 卡片网格用 CSS `grid-template-columns: repeat(auto-fill, minmax(140px, 1fr))` 自适应列数。
- 卡片内不嵌套 Naive UI 主题变量（`var(--n-color)` / `var(--n-color-target)` 等）——这些是 Naive UI 主题色（可能为紫/靛蓝），会导致卡片渲染成主题色。卡片 CSS 用固定色值（`rgba(128,128,128,0.2)` 等中性灰）。
- 卡片信息区（`.card-body`）扁平布局：model + pred + stats + video-name 四行，无嵌套 flex 行。
- 状态标记用纯色字（`.st-ok` 绿 / `.st-err` 红）而非 `<n-tag>`（n-tag 受主题色影响）。

**标注视频（margin 边条）**：
- cv2 叠字不要画在帧上（覆盖画面内容），改用 **margin 边条**：pad 画布，上边条放 GT(绿)+pred(黄/红)，下边条放 top5，中间原帧不动。
- cv2 不支持 Unicode（✓/✗ 显示 ???）——用颜色区分对错（绿=对，红=错），不用 Unicode 符号。
- 标注视频必须 H.264（`avc1`）编码——浏览器 `<video>` 不支持 mp4v（cv2.VideoWriter 默认）。用 ffmpeg 转码（imageio_ffmpeg 自带 libx264）。

**可视化样本（训练 Hook）**：
- 训练中用 mmengine Hook（`VisSamplesHook`）每 N epoch 生成 6 张 val 样本预测图。
- 按 epoch 分组存 `vis_samples/epoch_N/sample_K.jpg + meta.json`。
- 详情页按 epoch 分卡片，组内左右箭头 + 缩略图条切换。

**API 调用**：
- 并发请求用 `Promise.all`，不要串行 await（3 个请求串行 = 3 倍延迟）。
- 缓存策略：列表页切换回来时不要重新 fetch（用 `keep-alive` 或本地缓存），除非用户主动刷新。
- 防抖：搜索输入框 debounce 300ms，不要每敲一个字就发请求。

