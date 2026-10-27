# 迁移设计

## 已确认事实

- 本机 `datasets/cat_raw` 有 2,737 个视频、原始 CSV/JSON、3,927 条区间记录，
  5,480 个源文件按服务器源 SHA-256 全量核验通过，数据目录约 9.3 GiB。
- `自作自偷/cat_raw.tar.part-*` 是约 9.3 GiB 的重复传输归档，原数据已解包且验证；
  不再复制分卷。`自作自偷/4090.txt` 含登录口令，严格排除。
- 本机源码、说明、研究结果约数百 MiB，`results/npm-cache` 约 290 MiB 是可再生缓存。
  本机无公司服务器已缓存的约 7.96 GiB 公共模型文件实体；只有清单与少量安装归档。
- 课题组服务器为 `wyy@115.154.235.243:22108`，主机
  `xuwangyang-System-Product-Name`，2× RTX 4090 D，`/home` 约 11 TiB 空闲。
  已有 `/home/wyy/pet-action-recognition`，其中 checkpoint 约 5.5 GiB、
  results 约 72 GiB；已有 `/home/wyy/miniconda3/envs/pet` Python 3.10.20。
  NAS `/home/wyy/mnt` 当前挂载。目标 `/home/wyy/pet-final` 原先不存在。

## 迁移集合和布局

在新路径保留 Git 版本历史、项目顶层源码/配置/文档/方案图/项目要求、
`.claude` 项目技能、OpenSpec、研究输出中不可轻易重建的报告与本机未提交文件。
将 `datasets/cat_raw` 全部迁入同名目录，但其 `.local` 地址副本中的 Windows
绝对路径需要在服务器生成新的 Linux 路径副本；原始标注和相对路径版不改。

排除 `.venv`、`node_modules`、`__pycache__`、凭据文件、原分卷、下载缓存和
开发临时文件。数据与代码放在一个新工作目录，便于用户在课题组服务器继续开发。
保留对旧项目及其 checkpoints 的引用记录；如需复用权重，优先在新目录中创建
独立副本或明确的只读路径配置，不能让新训练输出覆盖旧 checkpoint。

使用项目内 `scripts/migration/migrate_pet_final_to_lab.py`：先入 Git，建立可恢复的文件清单，
密码从本机指定文件读取，使用已保存的 SSH host key 核验目标身份；以 SFTP 将
文件写到远程新目录的临时名字，校验后原子更名。已有同路径文件只在大小和
SHA-256 与本次源一致时跳过；冲突报错。大文件中断后从临时文件续传；不覆盖
原有课题组项目。最终在服务器按清单逐文件 SHA-256 核验，并保存无凭据报告。
传输来源的 manifest 明确记录所有排除项，避免把“仓库文件已复制”误报成
“公司服务器缓存的全部公开模型资产也已迁移”。

完成复制后只读检查新目录内的代码、视频、标注、CUDA/Python/PyTorch 与已有
checkpoint 可用性。对尚缺的公共权重或依赖，优先复用课题组服务器现有资产，
再使用本机保存的固定清单重新下载/安装必要项，核对哈希。任何无法恢复的资产
如实列出。未经过额外数据适配，不启动正式训练或大规模前向。

## 验收

新目录文件数量、字节和 SHA-256 与本机选定清单一致；原始猫数据清单
5,480/5,480 保留；原项目和旧权重不变。能在服务器找到 2,737 个视频、原始
标注和 3,927 条区间。代码可以用现有 4090 环境导入，模型权重/可选依赖的
实际缺项有明确列表及重建位置。报告记录总传输量、目标路径及受限事项。

## 2026-10-27 迁移记录复核

目标 `.migration/transfer_report.json` 记录于 2026-10-23T10:09:25Z 完成传输：7571 个文件、10,046,488,364 字节，`remote_sha256_verified: true`，代码 HEAD 为 `9847f1fde25fe52a0c3d29d91fcf0e07f6726e73`。这是当时的全量哈希验收记录，本轮未重算全部文件哈希。

只读复核确认目标有 2737 个正常视频、Linux 路径版 CSV 2626 行，以及 `/home/wyy/.pet-final-transfer/git_history.bundle`。`results/migration_lab/existing_checkpoints.json` 保留既有 checkpoint 检查记录。脚本现已归入 `scripts/migration/`。

`public_assets_missing_from_local: true` 明确表明公司公共资产缓存未全量迁入；不能宣称全部模型已经具备运行条件。Linux CSV 存在与行数正确不等于全部路径可读验收；未覆盖旧项目、凭据排除、先提交再执行及双端报告仍需逐项补足对应证据后勾选。不得把迁移后单独完成的训练替代这些验收记录。
