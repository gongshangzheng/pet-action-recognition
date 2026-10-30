# 将本地 pet-final 迁入课题组 4090 服务器

2026-10-23 用户明确指示“直接根据本地记录确认一下要搬什么，直接搬过去”，并将
课题组服务器的连接方式放在本机 `自作自偷/4090.txt`。此指示构成本 change 的实施
授权；迁移仅限用户已确认可自行迁移的课题组数据、项目代码及其公开依赖/权重。

目标：在课题组服务器新增 `/home/wyy/pet-final`，保留可运行代码、原始猫视频与标注、
恢复审计、项目文档、OpenSpec 和必要研究结果。现有 `/home/wyy/pet-action-recognition`
及其已训练权重、数据集和环境不得覆盖。传输时校验文件数量、大小和 SHA-256；
最终给出位置、验证情况及因不在本机而无法直接搬运的资产清单。

连接口令只从本机指定文件临时读取，绝不复制到服务器、仓库、清单或日志。
不复制本机 Windows 虚拟环境、浏览器/Node 缓存以及已解包数据的重复分卷。

## 2026-10-27 迁移记录复核

目标 `.migration/transfer_report.json` 记录于 2026-10-23T10:09:25Z 完成传输：7571 个文件、10,046,488,364 字节，`remote_sha256_verified: true`，代码 HEAD 为 `9847f1fde25fe52a0c3d29d91fcf0e07f6726e73`。这是当时的全量哈希验收记录，本轮未重算全部文件哈希。

只读复核确认目标有 2737 个正常视频、Linux 路径版 CSV 2626 行，以及 `/home/wyy/.pet-final-transfer/git_history.bundle`。`existing_checkpoints.json` 位于远端 `/home/wyy/pet-final/results/migration_lab/existing_checkpoints.json`，保留既有 checkpoint 检查记录。脚本现已归入 `scripts/migration/`。

`public_assets_missing_from_local: true` 明确表明公司公共资产缓存未全量迁入；不能宣称全部模型已经具备运行条件。Linux CSV 存在与行数正确不等于全部路径可读验收；未覆盖旧项目、凭据排除、先提交再执行及双端报告仍需逐项补足对应证据后勾选。不得把迁移后单独完成的训练替代这些验收记录。

## 2026-10-29 收尾结论

标注路径可读性已用 `scripts/checks/check_lab_annotation_paths.py` 实测通过：lab CSV 2626 行、
relative CSV 2626 行、intervals 3927 行、lab JSON 2737 个任务全部 `is_file()` 且非空，
磁盘 2737 个 mp4、约 9.3 GiB。此前"CSV 存在且行数正确"的间接证据已由直接检查取代。

本机 `~/.ssh/config` 新增 `Host lab`，走密钥认证；原口令文件 `自作自偷/4090.txt` 在本机已不存在，
仅影响需要重跑传输类脚本的场景，不影响只读核验。

仍未验证的一项：新目录内跑通训练/推理所需的环境与公共权重。`public_assets_missing_from_local: true`
表示约 8 GiB 公共模型缓存未随迁，是否补齐取决于后续是否在该机训练——当前主线训练在 `pet` 执行。
因此本 change 的结论是"迁移与数据完整性已验证，端到端可用性未验证"，不得表述为"迁移完成可用"。
