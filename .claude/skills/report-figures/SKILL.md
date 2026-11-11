---
name: report-figures
description: |
  报告级图的产出规范：把 Mermaid 排期/流程/时序图渲染成 PNG/SVG（含甘特图排版坑位），
  手写可编辑 SVG（方法示意图、架构图、多面板组图），LaTeX 公式矢量化，PDF/PNG 导出与物理尺寸控制。
  触发场景：(1) 图要放进报告、PPT、验收材料，需要静态图片而不是内嵌代码块，
  (2) 画方法示意图/系统架构图/多面板图，(3) 图里要放 LaTeX 公式，
  (4) 导出矢量 PDF 或指定宽度（如单栏 89mm）的印刷版，(5) Mermaid 甘特图排版异常（今天红线、泳道名压到任务条上、文字被裁剪）。
  不适用：定量统计图（准确率曲线、混淆矩阵、消融柱状图）用仓库自己的 Python 绘图链路，画完再回到本 skill 组图。
---

# 报告级图

本 skill 管两件事：**把文本图渲染成可交付的图片文件**，以及**手写可编辑的矢量图**。定量统计图不在这里。

## 1. 选路

先判断这张图是什么类型，再动手：

| 图类型 | 走哪条路 | 产物 |
| --- | --- | --- |
| 流程、时序、排期、状态机 | Mermaid 源文件 + `scripts/render_mermaid.sh` | PNG（2 倍）+ SVG |
| 方法示意、系统架构、多面板组图 | 手写 SVG（§3）或 Mermaid flowchart 兜底 | SVG / PDF / PNG |
| 图里有公式 | 手写 SVG + `svg_tools.py formula`（§4） | SVG（字形为路径）+ `.tex` |
| 准确率曲线、混淆矩阵、柱状图 | **不用本 skill**：用仓库自己的 Python 绘图链路导出 SVG，再按 §5 组图 | 由绘图链路决定 |

判断口径：**这张图要被人再编辑吗**。要 → SVG 路线（Mermaid 或手写都产出 SVG）；只是一次性贴进文档 → PNG 就够，但仍保留源码。

## 2. Mermaid → 图片

### 2.1 用法

```bash
# 首次：mmdc 需要一个 Chrome 内核
npx puppeteer browsers install chrome-headless-shell

# 渲染：<input.mmd> [输出基名]
.agents/skills/report-figures/scripts/render_mermaid.sh path/to/gantt.mmd
```

脚本做三件事：临时生成 puppeteer 配置（本机 Chrome 路径只在运行时存在，不入库）→ 用 `scripts/mermaid-render-config.json` 统一主题 → 同时输出 `-s 2` 的 PNG 与 SVG。

配置和源码一起入库，改图只改 `.mmd`，不要手改 PNG。

### 2.2 必须用 `-c` 传配置，不要只写在 init 指令里

`%%{init: {"themeVariables": {...}}}%%` 在 mmdc 12.0.0 + mermaid 12.1.0 下**实测不生效**：渲染出的 SVG 仍是默认 `fill:#8a90dd`、`.crit{fill:red}`。主题变量一律经 `scripts/mermaid-render-config.json` 由 `-c` 传入；`themeCSS` 负责覆盖 Mermaid 自己的类（`.task0`、`.crit1`、`.grid .tick`、`.today`）。

### 2.3 甘特图坑位（每条都来自实际返工）

| 现象 | 原因 | 做法 |
| --- | --- | --- |
| 图里有一条红色竖线 | Mermaid 默认画 `todayMarker`（系统当天） | 静态图关掉：`.mmd` 里 `todayMarker off`，配置里再兜一层 `.today{display:none}` |
| 左侧泳道名和任务条重叠 | `section` 标题是左对齐文本，`leftPadding` 默认只有 75px，中文名一长就压进时间轴 | `gantt.leftPadding` 与 `gantt.gridLineStartPadding` 同时调到 ≈240，留出独立标签列 |
| 任务名被裁一半、或挤到条外 | 单日条宽度装不下中文标签 | 标签压到 8–10 字，细节挪进正文表格；必要时把 1 天任务拉成 2 天 |
| 渲染直接报 `Cannot read properties of undefined (reading 'type')` | 任务名里含 `:`，被当成字段分隔符切碎 | 任务名里不用冒号，改写为 `周二·集成预审` 这类连接符 |
| 没有竖向网格线 | mermaid 12 把日期刻度线画在负坐标，被 viewBox 裁掉 | 已知行为，不要为此改坐标轴；靠轴标签读日期 |
| 中文变成方框或间距奇怪 | 无头浏览器缺中文字体 | 配置里 `fontFamily` 写本机可用字体（如 `'PingFang SC'`），导出后**打开看一遍** |

### 2.4 尺寸

- 画布宽度由 `render_mermaid.sh` 里的 `defaultViewport.width` 决定（默认 1900）。工期格数多就把宽度往上调，直到每格 ≈130px、条内文字不再被挤。
- PNG 用 `-s 2` 超采样，保证贴进 PPT 不糊；需要无损放大就用同名 SVG。

## 3. 手写 SVG

真实、可编辑的 SVG 源文件，不要用 AI 生成位图替代矢量图。

- 显式写 `viewBox`、SVG 命名空间和最终物理尺寸。单栏起点用 `width="89mm"` 配等比高度，实际以目标期刊/模板要求为准。
- 标签用 `<text>` 并显式给坐标与 `text-anchor`，不要依赖 HTML 布局或 `foreignObject`。
- 用 `<g>` 表示有意义的整块对象，`<rect>`/`<path>` 画几何，`<marker>` 做箭头，`<title>`/`<desc>` 写图意。
- 面板、线型、箭头样式跨图保持一致；数据图要连同绘图脚本和原始数据一起保留。
- 辅助脚本只接受受控子集：拒绝 `<style>` 块、外部资源与可执行内容，允许 PNG/JPEG 的 data URI。**这是创作子集，不是恶意 SVG 的净化器。**

几何、排版、字体的完整规则见 [references/svg-latex.md](references/svg-latex.md)。修改已有图（对比面板、重新渲染、分阶段替换）见 [references/editing-existing.md](references/editing-existing.md)。

## 4. 公式

SVG 的 `<text>` 里写 `$...$` 不会渲染成公式。要矢量字形就走 `formula`：

```bash
python3 scripts/svg_tools.py formula --input equation.txt --output equation.svg
```

`equation.txt` 只写数学内容，不带 `$` 和文档包裹（支持 amsmath/amssymb 片段，不支持 TikZ、PSTricks、外部图片）。命令同时留下 `.tex` 源，字形是路径、不可当文本编辑，所以两边都要保留。

其它路线（MathText、Inkscape TexText、PDF+LaTeX 双文件）的适用条件见 references。

## 5. 组图与导出

```bash
python3 scripts/svg_tools.py doctor                     # 只报依赖，不安装
python3 scripts/svg_tools.py prepare /path/figure-dir   # 建可编辑骨架
python3 scripts/svg_tools.py compose --spec composition.json --output figure.svg
python3 scripts/svg_tools.py inspect figure.svg         # 导出前检查
python3 scripts/svg_tools.py export figure.svg --backend cairosvg --output figure.pdf --width-mm 89
python3 scripts/svg_tools.py export figure.svg --backend cairosvg --output preview.png --width-mm 89 --dpi 300
```

- `compose` 会内联子图、给 ID 加命名空间、拒绝缺失引用和越界摆放；composition 里的路径相对 JSON 所在目录。
- `export` 依次尝试 `cairosvg` → `inkscape` → `rsvg-convert`，也可用 `--backend` 强制；**缺依赖或转换有告警就是错误**，不许悄悄换引擎或删公式。
- 输出一律新建，覆盖会被拒绝。

## 6. 验收

渲染出来按**目标宽度**看一眼，检查：箭头走向、对齐、公式大小与基线、裁剪、上下标、字形、标签可读性。`inspect` 只校验受限的静态子集，不保证布局、科学正确性、字体可用性或编辑器兼容性。

交付时保留：SVG 源、公式片段与生成的 `.tex`、composition JSON、最终导出件。

## 7. 落点

| 内容 | 位置 |
| --- | --- |
| 文档配图 | `management/docs/_assets/<slug>/`，`<slug>` 与所属文档对齐 |
| 图的源码（`.mmd`、SVG 源、composition JSON、渲染配置） | 与图片同目录，一起入库 |
| 只在仓库内一次性使用的渲染脚本 | `scripts/checks/`，由该目录 README 说明用法 |

图号与图题写法见 `documentation` skill（`![图 N · 说明](url)`）。
