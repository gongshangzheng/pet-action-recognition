## Why

任务书第一阶段（7–8 月）要求「选定候选模型」，检测链候选（YOLO11）至今未做任何实测；t13-1（9 月启动）依赖两件现在就能做的事：**选型证据**（COCO 预训练在猫/人/碗上到底行不行、夜视红外漏多少）和**标注类目定稿**（类目错了回补成本翻倍）。三件零 GPU 训练成本的准备工作本周并行，为 t13-1 铺路并防止返工。

## What Changes

- **新增 zero-shot 体检脚本**：COCO 预训练 YOLO11（n/s 两档）对 79 段 cats 视频批量推理，按白天/夜视（小时 + 帧亮度双口径）分组统计 cat/person/bowl 检出率与置信度，产出 Markdown/JSON 体检报告 + 抽样标注视频
- **新增预标注产物**：按最终类目映射（COCO cat→猫、person→人、bowl→食盆/水盆合并预标）导出 YOLO 格式帧 + LabelStudio 可导入任务包（含 predictions），9 月 t13-1 人工只做修正，标注提速一倍以上
- **标注类目定稿决策文档**：在 t13-1 原类目（猫、人、食盆、水盆、猫砂盆、玩具、门窗）基础上增加 `cat_face`（中期验收「面部暴露面积占比」需要），附类目定义、验收特征映射、COCO 预标注类映射表
- **骨架复活验证实验排期**：把 wiki《复活条件分析》中的实验（检测框→BoT-SORT→贴边门控→AP-10K）排进 t13-1 验收后第一周，写入 tasks.json
- **更新 t13-1 任务描述**：description 引用定稿类目文档

## Capabilities

### New Capabilities

- `detection/yolo11-prep`：检测链第一阶段准备——zero-shot 体检（选型证据 + 夜视漏检量化）、预标注帧产出（LabelStudio 可导入）、标注类目定稿（含 cat_face 与验收特征映射）

### Modified Capabilities

（无——`speedrun-results` 与本变更无关，检测域尚无存量 spec）

## Impact

- **新增脚本**：`scripts/yolo11_zeroshot_audit.py`（批量推理 + 统计 + 预标注导出，单文件 CLI）
- **新增依赖**：`ultralytics`（pet 上安装；本地不装不跑）
- **数据输入**：pet `/home/wyy/mnt/cats/` 的 79 段视频（datasets/cats 同源，无需重新上传）
- **产物落盘**：pet `results/detection/zeroshot_cats/`（报告、抽样视频、预标注包）， NAS 备份按现有惯例
- **管理文件**：`management/docs/` 新增类目定稿文档；`management/projects/pet-action-recognition/tasks.json` 更新 t13-1 description 与排期 note
- **不改动**：训练 registry、speedrun 模块、live 模块、前端页面
