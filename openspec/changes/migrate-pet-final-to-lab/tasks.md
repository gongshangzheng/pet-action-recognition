# Tasks

## Plan / Review

- [x] 读取本地恢复报告和服务器现状，确认连接身份、容量与目标路径。
- [x] 固定迁移范围和凭据排除项。
- [x] 用户 2026-10-23 明确指示直接迁移，进入 Apply。

## Apply

- [x] 提交可复用迁移脚本与本 change。**顺序未遵守**：`scripts/migration/migrate_pet_final_to_lab.py` 首次入库为 2026-10-27 `c9fa6b6`，晚于 2026-10-23 的实际传输。此项不可事后补做，如实记录。
- [x] 生成无凭据本机文件清单与 Git 历史 bundle。远端 `.migration/manifest.json` / `manifest.sha256` 逐文件记录 7571 项哈希；`/home/wyy/.pet-final-transfer/git_history.bundle` 已迁。本机 `results/migration_lab/` 为 gitignore 目录，未长期保留，哈希证据以远端副本为准。
- [x] 在 `/home/wyy/pet-final` 建立独立项目，上传源码、文档、项目研究产物及猫数据。
- [x] 校验目标数量、大小、SHA-256，记录失败和续传状态。远端报告 `remote_sha256_verified: true`。
- [x] 生成服务器 Linux 路径版标注，复查原标注、相对索引和全部视频可读。2026-10-29 用 `scripts/checks/check_lab_annotation_paths.py` 复验：lab CSV 2626 行、relative CSV 2626 行、intervals 3927 行、lab JSON 2737 个任务，`missing=0 empty=0`，磁盘 2737 个 mp4。产物 `results/migration/lab_path_check.json`。
- [ ] 核对课题组既有运行环境及 checkpoint，补齐必要公开资产或报告缺项。**未完成，且需用户先决定是否在 lab 训练**：`public_assets_missing_from_local: true`（约 8 GiB 公共权重未随迁），既有 `/home/wyy/pet-action-recognition` 的 checkpoint 与 `pet` conda 环境是否可复用尚未绑到新目录。当前主线训练在 `pet` 上执行，此项不阻塞现有工作。
- [x] 保存迁移报告，给出使用入口和后续训练限制。见本文末"使用入口与限制"。
- [x] 确认未覆盖原 `/home/wyy/pet-action-recognition`，未迁移口令或缓存。原目录仍在（含约 5.5 GiB checkpoint、约 72 GiB results）；口令文件 `自作自偷/4090.txt` 从未进入 Git，`.gitignore:33` 整目录排除，且该文件在本机已不存在。

## 2026-10-27 迁移记录复核

目标 `.migration/transfer_report.json` 记录于 2026-10-23T10:09:25Z 完成传输：7571 个文件、10,046,488,364 字节，`remote_sha256_verified: true`，代码 HEAD 为 `9847f1fde25fe52a0c3d29d91fcf0e07f6726e73`。这是当时的全量哈希验收记录，本轮未重算全部文件哈希。

只读复核确认目标有 2737 个正常视频、Linux 路径版 CSV 2626 行，以及 `/home/wyy/.pet-final-transfer/git_history.bundle`。`existing_checkpoints.json` 位于**远端** `/home/wyy/pet-final/results/migration_lab/existing_checkpoints.json`（由 `scripts/migration/finish_lab_migration.py` 写入），不是本机路径。脚本现已归入 `scripts/migration/`。

`public_assets_missing_from_local: true` 明确表明公司公共资产缓存未全量迁入；不能宣称全部模型已经具备运行条件。不得把迁移后单独完成的训练替代这些验收记录。

## 2026-10-29 收尾复核

- 标注路径可读性已实测通过（见上），此前只验证过"CSV 存在且行数正确"，现已升级为逐行 `is_file()` + 非空检查。
- 连接方式：本机 `~/.ssh/config` 新增 `Host lab`（SSH 密钥登录）。原 `自作自偷/4090.txt` 口令文件在本机已不存在，迁移脚本的 `connect()` 依赖该文件，重跑传输类脚本前需先恢复凭据来源；只读检查脚本改用系统 `ssh`，不依赖任何口令。
- 仍未验证的只有一项：新目录内实际跑通训练/推理的完整环境与权重。这是唯一会让"迁移完成"变成"迁移并可用"的缺口。

## 使用入口与限制

- 代码与数据：`/home/wyy/pet-final`（独立项目，与原 `pet-action-recognition` 并存）。
- 猫数据：`/home/wyy/pet-final/datasets/cat_raw`，2737 个 mp4，约 9.3 GiB；标注在 `annotations/`，`merged_annotations.lab.*` 为 Linux 绝对路径版，`merged_annotations.relative.*` 为相对路径版，原始 Label Studio 导出保留在 `annotations/original/`。
- Git 历史：bundle 在 `/home/wyy/.pet-final-transfer/git_history.bundle`。
- 限制一：默认整视频单标签入口不能直接用这份区间标注，需要先做片段切分或适配。
- 限制二：公共模型权重未全量随迁，运行前需确认能否复用旧目录权重，否则重新下载并核哈希。
- 限制三：旧目录 `/home/wyy/pet-action-recognition` 的 checkpoint 与 results 不可覆盖，复用请走独立副本或只读路径配置。
