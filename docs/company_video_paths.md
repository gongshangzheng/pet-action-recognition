# 公司视频地址映射副本

只修复 Label Studio 视频地址，不改变动作标签、起止区间、其他字段或记录顺序。
空标注、取消标注和多标签记录也保留。原始标注与视频不覆盖、不移动。

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
