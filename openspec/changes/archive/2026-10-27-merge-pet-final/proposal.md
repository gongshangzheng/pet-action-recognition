## Why

远程 pet-action-recognition 停留在 ae88715；pet-final/main 在此基础上增加 56 个提交，最新猫动作实验又在 cat-action-v1 分支。需要将已验证的训练工作整合回当前仓库，避免误以为代码合并会自动带回权重。

## What Changes

- 在本地整合 pet-final/main 的迁移、数据审计和运行准备代码，保留当前 main 的 Web 改进。
- 默认同时纳入 cat-action-v1 已提交的七类猫动作数据准备、六模型训练和评测代码；审核时可缩减为仅合并 main。
- 审计 pet-final 未提交内容，区分 CRLF、权限变化和真实修改，逐项决定，不整体复制脏工作树。
- 权重与数据保留在原路径；另行核验现有运行入口能否显式使用这些路径，不复制大文件；在远程 checkpoints/cat_action_v1/<model>/ 下为最佳权重建立非覆盖软链接。

## Capabilities

### New Capabilities

- `cat-action-integration`: 整合猫动作训练代码、配置及现有权重定位信息。

### Modified Capabilities

无。本 change 的增量规格仅约束整合验收；已有来源分支中的规格保留并在实施时审计。

## Impact

涉及 configs、scripts、petlib、docs、openspec 和部分 Web/训练路由；不迁移数据库、环境、数据集或权重，不启动训练，不修改原 pet-final 工作树。实际冲突和依赖变更待批准后获取 Git 对象并试合并确认。

## 用户确认的合并后整理

2026-10-27 用户确认先合并再迁移：自动化测试归 tests/，预检/烟测归 scripts/checks/，部署/迁移/环境恢复归 scripts/migration/，正式实验入口保留 scripts/。同步修正根路径、导入和当前文档命令；测试夹具归 results/tests/。权重用软链接接入。
