# 公司视频地址映射副本

只修复 Label Studio 视频地址，不改变动作标签、起止区间、其他字段或记录顺序。
空标注、取消标注和多标签记录也保留。原始标注与视频不覆盖、不移动。

## 2026-10-10 执行结果

已生成副本并通过独立回读核验：CSV 2,626/2,626 行、JSON 2,737/2,737 个任务
全部映射到可读视频，共引用 2,737 个正常视频；2,737 个 AppleDouble 文件未参与。
上传前缀解析覆盖 CSV 1,574 行、JSON 1,638 个任务；`d` 参数解析覆盖 CSV 1,052 行、
JSON 1,099 个任务。跨 CSV/JSON 的 2,626 个相同任务 ID 的视频地址一致。
CSV 非地址字段（包含 `behavior` 原始字符串）、JSON 非地址内容与原值一致，
原 CSV/JSON 的 SHA256 不变，视频大小/mtime/inode 不变。

本次审计目录：
`/home/work/analysis_code/results/datasets/company_video_paths_20261010T085713Z_d1e8d962/`，
包含 `path_mapping.csv` 与 `report.json`。没有进行训练、前向、视频解码或标签转换。

## 路径

源目录：`/home/work/pet_analysis_wyy`。
公司项目：`/home/work/analysis_code`。

默认副本：

- `datasets/company_video_paths/merged_annotations.local.csv`，只替换 `video`。
- `datasets/company_video_paths/merged_annotations.local.json`，只替换 `data.video`。

副本中的视频地址直接指向 `/home/work/pet_analysis_wyy/dataset-wyy/` 下的真实文件。
映射表和核验摘要在 `results/datasets/company_video_paths_<执行时间>/`；
实际目录由脚本终端输出的 `audit_dir` 给出。

## 服务器命令

已批准 change 后，使用现有环境，不需要安装依赖：

```bash
cd /home/work/analysis_code
.runtime/pet/bin/python -B scripts/normalize_company_video_paths.py --self-test
.runtime/pet/bin/python -B scripts/normalize_company_video_paths.py --check-only
.runtime/pet/bin/python -B scripts/normalize_company_video_paths.py
.runtime/pet/bin/python -B scripts/normalize_company_video_paths.py --verify-only
```

`--check-only` 和 `--verify-only` 不写文件。正常执行会生成标注副本与独立审计。
已有不同内容的副本不会被覆盖；未知地址、缺失、不可读或歧义都会报错。
审计包括原标注 SHA256、映射方式计数、非地址字段比较和视频大小/mtime/inode检查。
只检查路径与读取权限，不解码视频、不启动训练或前向。

CSV 的 `behavior` 字符串保持原值；副本的 CSV 引号和 JSON 缩进可能与原文件不同。
原 CSV/JSON 的字节内容及 SHA256 保持不变。

## 使用边界

这是本地路径版 Label Studio 标注，仍保留原有动作区间格式。
不是 MMAction2 VideoDataset 的 `<路径> <类别整数>` 列表；后续正式训练接入时
还需按原标注语义读取区间，本次没有进行该转换，也没有修改现有训练脚本。

## 帧区间、重叠与未标注空隙（2026-10-10 只读结论）

用户说明：摄像头自动切出有猫出现的视频，再按行为标注帧区间；
不同猫的动作可能重叠，视频内也可能有未标注帧。此类标注可以作为训练来源，
但当前正式训练入口不能直接使用。`scripts/train_model.py` 创建的是
`VideoDataset`；其标注读取器只读取视频路径与类别整数，不读取
Label Studio 的 `ranges` / `timelinelabels`。打开 `multi_class` 可以表示
一个视频样本的多个类别，仍不会自动保留时间区间或猫的身份。

按示例假定帧号从 1 开始且包含两端：1–50 帧活动，40–100 帧进食，
则 1–39 帧为活动、40–50 帧同时活动和进食、51–100 帧为进食。
不同猫造成的重叠可以是有效的多标签监督，不应强行选一个类别。
正式转换前仍须核对标注模板中的单位、帧号基数与端点语义。

空隙只能先视为未标注，不能默认赋予“无动作”或“无猫”标签。
若标注不穷尽，不能把所有未出现的类别直接当负例；需要明确监督范围，
再决定忽略相应位置/类别的损失还是补标。自动有猫切片也不能替代
逐帧存在性标注或无猫负样本，尤其不能直接监督检测延迟造成的片尾。

后续建议保留原标注，建立独立的区间/短窗训练索引与多标签训练配置；
原视频可按索引读取，不一定要物理切出新视频。时间窗跨动作边界时须
明确定义目标和监督掩码，不能给整段视频简单挂上区间中的某一个类别。
划分训练/验证集时应让同源连续片段保持在同一组，避免重叠窗口泄漏。
仅有动作与时间可以监督场景行为；若要区分每只猫，需核对是否已有
猫 ID、框或轨迹关联，尚未完成该字段审计，不能认定现有标注含个体监督。

此前训练检查仅用两个区间验证少量反向步骤，并非上述完整适配验收。
本节仅记录只读分析，不转换标签、不启动训练，也不扩展已批准的地址修复范围。
