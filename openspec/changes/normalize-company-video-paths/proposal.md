# 公司视频地址映射修复

## 目标与范围

用户要求解决 `/home/work/pet_analysis_wyy` 中标注引用与实际视频的地址映射，
并明确要求暂不修改标注内容。本 change 只生成本地绝对路径版标注副本；
不改变动作标签、起止区间、任务 ID、标注状态或其他字段值，不修改原文件。
不切片、不转换训练标签、不划分数据集、不启动训练、前向或模型评估。

原视频：`/home/work/pet_analysis_wyy/dataset-wyy/`。
原标注：`/home/work/pet_analysis_wyy/annotation-wyy/merged_annotations.csv`、
同目录的 `merged_annotations.json`。

之前只读诊断发现，两种 Label Studio 引用分别为 `/data/upload/...` 和
`/data/local-files/?d=...`。后者的文件名在 `d` 参数中，旧读取逻辑遗漏它，
造成 1,052 条记录未匹配；修正解析后，所有 CSV/JSON 视频引用都能匹配。
该结论不是本次重新核验，实施时须检查当前文件是否发生变化。

## 具体产物

在 `/home/work/analysis_code/datasets/company_video_paths/` 生成：

- `merged_annotations.local.csv`：仅替换 `video` 字段。
- `merged_annotations.local.json`：仅替换各任务的 `data.video` 字段。

替换后的值为实际存在的绝对路径，例如
`/home/work/pet_analysis_wyy/dataset-wyy/<实际文件名>.mp4`，不依赖 Label Studio 服务。
旧地址到新地址的映射和核验摘要保存在项目 `results/datasets/` 下的本次专属目录，
不向标注副本添加审计字段，不向本机传输公司视频或标注内容。

新增可复用脚本 `scripts/normalize_company_video_paths.py`，先提交再在服务器执行。
脚本同时提供只读核验入口。使用现有 Python 标准库，不安装或下载依赖。

## 验收

每条地址均对应唯一、可读、位于视频根目录中的正常视频；不能匹配时明确报错，
不使用时间戳或模糊匹配。CSV/JSON 除允许替换的地址字段外逐字段相等，
CSV 的 `behavior` 原始字符串也必须保持相同。原标注 SHA256 不变；
不改名、移动、复制或重编码视频。不声明已经完成 MMAction2 标注格式转换。

## 审核状态

Plan 已完成，等待用户明确批准本 change。旧 SSH 会话已断开；获批后重连，
在实际密码提示出现时再请用户提供新的动态口令。旧口令不复用、不持久化。
