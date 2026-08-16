## 1. 环境与数据就绪（pet）

- [x] 1.1 pet 上新建 conda env `yolo`（python 3.11 + torch 2.8.0+cu128 + ultralytics），验证 `yolo11n.pt`/`yolo11s.pt` 权重可下载、单视频推理冒烟通过
- [x] 1.2 确认 `/home/wyy/mnt/cats/` 下 79 段视频可解码（ffprobe 批量过一遍，坏档清单入产物 README）

## 2. 标注类目定稿

- [ ] 2.1 撰写 `management/docs/detection-annotation-taxonomy.md`：类目表（cat/person/food_bowl/water_bowl/litter_box/toy/door_window/cat_face + 预标注中间类 bowl_unspecified）、每类边界定义、验收特征映射表；标注版本号与评审状态
- [ ] 2.2 更新 tasks.json t13-1：description 引用类目文档（含 cat_face），progress 加骨架复活验证实验排期 note（验收后第一周，链接 wiki《复活条件分析》）

## 3. zero-shot 体检脚本

- [x] 3.1 实现 `scripts/yolo11_zeroshot_audit.py`：CLI 参数（--videos-root/--output/--models n,s/--conf 0.25/--frame-interval 2/--night-luma 60/--sample-per-group 4/--seed 42/--dry-run）
- [x] 3.2 逐帧记录落盘：per-video JSON（帧号、亮度均值、饱和度、各类检出与 conf），单视频解码失败跳过并记录，不中断整批
- [x] 3.3 汇总报告生成：report.md + report.json，含昼夜双口径分组（小时/亮度+饱和度 IR 判据）、n/s 对比、per-class 检出帧率与均值 conf、失败清单
- [x] 3.4 抽样画框视频：按夜视帧占比分层（夜视组/白天组各抽 4 段，seed 固定），框上标类名+conf

## 4. 预标注包导出

- [x] 4.1 YOLO 格式导出：`preannotation/yolo/{images,labels}` + `classes.txt`（定稿类目全集，单一事实源）
- [x] 4.2 LabelStudio tasks JSON 导出：predictions 用 rectanglelabels（百分比坐标），bowl→bowl_unspecified 映射，无检出帧带空标注导出
- [x] 4.3 产物 README：运行参数、阈值、类映射表、局限声明（单日单机位）

## 5. 执行与验收

- [x] 5.1 pet 上全量跑 n/s 两档，核对 report 数字与 sampled_videos 可播放
- [x] 5.2 人工抽检 8 段画框视频，形成选型结论（夜视漏检率、n vs s、预标注可用性判定）写入 report.md 结论节；若预标注不可用，执行 D5 降级路径（纯导帧）
- [ ] 5.3 类目文档 + t13-1 更新 + 体检报告提交 git（`feat: yolo11 zero-shot 体检与标注类目定稿`）
