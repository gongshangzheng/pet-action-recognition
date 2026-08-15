# speedrun-custom-config Tasks

## 脚本改造

- [x] **T1** `scripts/speedrun.py` 新增 `--custom model_id=config:ckpt`（可重复）参数，解析为 registry 同形条目，覆盖同名 registry 模型（warn）
- [x] **T2** 新增 `--ann-file` + `--label-map` GT 链：stem → label_idx → 类名 dict；`_gt_for(video)` 先查 dict，miss 回退父目录派生
- [x] **T3** custom 模型走分类分支复用 `infer_and_annotate`（含 `--label-map` 传入 classes.txt 作为其 label_map）

## 烟测（pet）

- [x] **T4** 1 模型（tsm）× 2 视频 + ann_file 烟测：标注视频有黑 margin + GT + top5，results.json 记录 `gt_label/correct/metrics.top5` 正确

## 全量重跑（pet）

- [x] **T5** 备份 results.json（.bak3）→ 3 模型 × 101 视频标准管线重跑（`--run-name cats-v1-speedrun --force`）→ rsync results.json 回本地

## 验证 + 文档

- [x] **T6** 页面抽查：cats-v1-speedrun 批次视频有黑 margin/GT/top5，准确率与重跑记录一致
- [x] **T7** 新建 `.agents/skills/speedrun/SKILL.md`：speedrun 权威入口（触发场景：跑/查/排坑 speed run）
  - 内容：CLI（含 `--custom`/`--ann-file`/`--label-map`/`--run-name`）+ API + 产物约定（outputs/<model>/、covers/、results.json 字段）+ 黑 margin 标注格式 + GT 链（ann_file 优先，父目录回退）+ 正确率 token 匹配 + H.264 转码 + 常见坑（registry 只认 400 类 → --custom；微调模型必须走标准管线；ffmpeg 缺失 → _transcode_h264；GPU 共享避坑）
- [x] **T8** 既有 skill 改为引用 + 修正：
  - `testing/SKILL.md`：Speed Run 章节精简为入口 + 指向 [[speedrun]]；GT 描述改为「ann_file 优先，父目录派生回退（UCF101）」
  - `evaluation/SKILL.md`：同步 GT 描述与 CLI 示例，指向 [[speedrun]]
  - `repo-structure/SKILL.md`：补 `web/src/api/speedrun.js`；SpeedRun.vue 位置 training → evaluation；skill 表补 speedrun 行（fix-speedrun-playback 遗漏）
