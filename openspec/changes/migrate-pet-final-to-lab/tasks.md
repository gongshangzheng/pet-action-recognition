# Tasks

## Plan / Review

- [x] 读取本地恢复报告和服务器现状，确认连接身份、容量与目标路径。
- [x] 固定迁移范围和凭据排除项。
- [x] 用户 2026-10-23 明确指示直接迁移，进入 Apply。

## Apply

- [ ] 提交可复用迁移脚本与本 change，先提交再执行。
- [ ] 生成无凭据本机文件清单与 Git 历史 bundle。
- [x] 在 `/home/wyy/pet-final` 建立独立项目，上传源码、文档、项目研究产物及猫数据。
- [x] 校验目标数量、大小、SHA-256，记录失败和续传状态。
- [ ] 生成服务器 Linux 路径版标注，复查原标注、相对索引和全部视频可读。
- [ ] 核对课题组既有运行环境及 checkpoint，补齐必要公开资产或报告缺项。
- [ ] 保存本地/远程迁移报告，给出使用入口和后续训练限制。
- [ ] 确认未覆盖原 `/home/wyy/pet-action-recognition`，未迁移口令或缓存。

## 2026-10-27 迁移记录复核

目标 `.migration/transfer_report.json` 记录于 2026-10-23T10:09:25Z 完成传输：7571 个文件、10,046,488,364 字节，`remote_sha256_verified: true`，代码 HEAD 为 `9847f1fde25fe52a0c3d29d91fcf0e07f6726e73`。这是当时的全量哈希验收记录，本轮未重算全部文件哈希。

只读复核确认目标有 2737 个正常视频、Linux 路径版 CSV 2626 行，以及 `/home/wyy/.pet-final-transfer/git_history.bundle`。`results/migration_lab/existing_checkpoints.json` 保留既有 checkpoint 检查记录。脚本现已归入 `scripts/migration/`。

`public_assets_missing_from_local: true` 明确表明公司公共资产缓存未全量迁入；不能宣称全部模型已经具备运行条件。Linux CSV 存在与行数正确不等于全部路径可读验收；未覆盖旧项目、凭据排除、先提交再执行及双端报告仍需逐项补足对应证据后勾选。不得把迁移后单独完成的训练替代这些验收记录。
