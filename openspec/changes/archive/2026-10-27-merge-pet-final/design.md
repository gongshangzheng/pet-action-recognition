## Context

只读检查日期：2026-10-27。远程旧仓库 main=ae88715，干净；本地 main=4a45102，干净。pet-final/main=9847f1f，比 ae88715 多 56 个提交，已提交差异 106 文件。cat-action-v1=eb63f7d73，比 pet-final/main 多 46 个提交。

pet-final 的原始 diff 涉及 1581 文件；忽略行尾空白后为 30 文件、93 行新增、1 行删除（其中含权限变化）。真实文本变化主要是运行环境 design 和静态文档构建脚本，另有未跟踪脚本。远程 pet-final 不含本地 4a45102 对象，因此目前尚未完成准确的试合并或冲突判断。

## Goals / Non-Goals

目标：把来源分支的已提交代码在本地可追踪地合并，保留本地 Web 功能，记录实验权重位置。非目标：移动数据、复制环境、重新训练、修改 pet-final 工作树。

## Decisions

- 使用本地独立整合分支，固定来源提交后依次合并 pet-final/main、cat-action-v1；不把远程目录整体覆盖到本地。
- 批准后通过 SSH fetch 来源分支到本地命名引用，执行试合并并记录冲突；保留两侧历史，不 force push。
- 来源未提交差异只读导出审计，排除换行与权限噪声。与可复现训练有关的真实差异逐项带入本地；其他改动记录为未纳入，未知含义不得静默覆盖。
- 最新最佳权重保留于 /home/wyy/pet-final/results/training/cat_action_v1/；核对六模型路径、大小、既有哈希和配置对应关系。训练代码合并不等于训练结果出现在 Web 页面。
- 默认完成本地合并与验证，再通过既有 pet remote 快进同步旧仓库；推送前重查远程工作树和 HEAD，不改 pet-final 和 pet-final-v1。权重通过已提交的幂等工具在 checkpoints/cat_action_v1/<model>/best.pth 建立绝对路径软链接，不覆盖任何既有文件；不移动源产物。

## Risks / Trade-offs

- Web 文档构建和重叠 OpenSpec 内容可能冲突 → 逐文件保留两侧有效变更，构建及文档路由冒烟验证。
- 来源代码带有机器路径或额外依赖 → 审计路径与依赖，不安装共享环境，不在本地执行 GPU 工作。
- 当前分支状态可能变化 → apply 时重新确认三个仓库及来源提交，记录审计差异。

## Migration Plan

整合前记录两端 HEAD，保存本地回退引用；本地合并与验证通过后提交，再快进同步 pet，验证 HEAD。出现冲突先停在本地整合分支解决；如已同步后需回退，以 revert 提交恢复代码，不重置远程历史。数据、权重、服务进程始终保持原状。

## 合并后目录迁移

已获用户确认：合并完成后迁移项目自动化测试、预检和运维脚本到 AGENTS.md 规定目录。优先使用根目录启动的模块导入或显式定位 parents，验证 CLI --help；所有内部调用同步更新。历史 OpenSpec、实验日志和旧审计记录保留历史路径，当前维护文档更新路径。测试临时目录显式位于 results/tests/。不迁移第三方或 skill 自带测试。

## 来源功能清单

pet-final/main 包含：AnimalKingdom 既有权重对比与报告、公司部署打包和校验、独立环境准备、离线资源下载与哈希审计、模型前后向预检、RV1126B 最小模拟器检查、标注路径规范化、标签/音频审计、分卷猫数据恢复、课题组迁移，以及 LFB 8xb12 注册修正。文档侧栏和静态构建与本地重叠，保留本地增强。

cat-action-v1 包含：区间数据集/采样/指标、小样本 smoke、七类映射过滤及按日划分、TSN/TSM 基线、四参考模型训练及验证排名冻结、权重与采样预检、均衡错误率/绘图/区间统计、迁移后环境与同步工具、CRLF frontmatter 构建兼容。它不实现连续视频事件检测、多猫身份关联或端侧量化。

## 实施与验证记录

来源固定为 pet-final/main@9847f1f 与 cat-action-v1@eb63f7d73；本地原始 main@4a45102，规范提交 4487462 可作为整合前回退点。两次 merge 保留来源历史；唯一冲突为 build-docs-data.mjs，保留本地排序、注释和资源构建逻辑，加入 CRLF 行拆分。

来源 main 的未提交换行符/权限变化未带入；额外运行环境 design 记录未纳入实现；CRLF 实际修复已包含在来源 cat-action-v1 提交中。来源未跟踪迁移脚本的已提交版本由 cat-action-v1 带入；.runtime、weights、数据、数据库和结果未复制。原来源工作树保持原状。

迁移 24 个入口：2 个自动化测试、10 个检查工具、12 个运维工具。另新增 1 个权重链接工具及其 4 项安全测试，清单含六模型配置与完整 SHA-256。新目录和当前文档引用已更新，来源 OpenSpec 和既有实验说明保留历史记录。

本地验证：11 个合成数据自动化测试通过；65 个 Python 文件 AST 解析、Shell bash -n、所选无模型 CLI --help 通过；Web npm run build 成功（保留原有大 chunk 提示）；11 篇静态文档、404 回退及 LF/CRLF frontmatter 等价检查通过；git diff --check 和 OpenSpec strict 校验通过。人工审查路径、非覆盖链接、配置/哈希对应和运行时文件未入库。未启动训练、推理、安装依赖或重启服务；GPU 预检本身未重跑。

六模型权重在远程完成 SHA-256 复核，与既有文档的完整哈希或前缀匹配；原文件在 pet-final/results/training/cat_action_v1。完整哈希见 configs/cat_action_v1_checkpoints.json。

## 同步与权重接入结果

本地 main 已快进并通过 git push pet main 同步到旧远程工作树（updateInstead）。已在 pet-action-recognition/checkpoints/cat_action_v1/ 下建立六模型的 best.pth 链接，均指向 pet-final 的既有最佳权重；工具执行前完整复核 SHA-256，未替换既有文件。远程报告为 results/migration/cat_action_v1_links.json，源数据、权重、运行环境和两个来源工作树未修改，未重启服务。

数据索引、原始猫视频和实验日志仍在 pet-final，未链接或迁移；本次链接不提供 Web run 注册。模型重跑需显式配置数据位置与环境，不能将代码合并视为整套运行资源迁移。
