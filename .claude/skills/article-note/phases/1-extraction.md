# Phase 1：Extraction

## 1. 生成 slug

使用论文关键词 + 年份，小写 kebab-case，例如 `maskgit-2022`、`attention-2017`。去掉标点、版本号和无意义停用词；同名论文追加短标题或 arXiv ID。slug 一旦进入 change 不再随意修改。

## 2. 初始化

```bash
python3 .agents/skills/article-note/scripts/init-workspace.py maskgit-2022 \
  --root .cache/article-note
```

工作区固定为：

```text
.cache/article-note/<slug>/
├── raw/sources/
├── raw/figures/
├── analysis/
└── synthesis.md
```

## 3. 来源优先级

```bash
python3 .agents/skills/article-note/scripts/fetch-paper.py \
  --input 2508.09959 --slug maskgit-2022 \
  --workspace .cache/article-note/maskgit-2022 --html --pdf
```

优先使用 arXiv source tarball；失败后尝试 arXiv HTML；最后下载 PDF。source 中的 TeX、caption、表格和图片是首选证据。脚本只写工作区，不写 wiki。

## 4. 图片

原图放在 `raw/figures/`，记录到 `figures-manifest.md`。不要在抓取阶段自动选择全部图片进入正文；图片选择属于主 agent 或 image-collection lane 的判断。

## 5. extraction-log

必须记录：时间、输入、尝试的来源、HTTP/解析结果、降级原因、输出文件、图片数量、缺失依赖和下一步回源指针。全失败时以非零状态退出并停止流程。
