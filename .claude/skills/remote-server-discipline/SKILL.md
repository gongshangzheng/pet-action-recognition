---
name: remote-server-discipline
description: |
  远程服务器交互纪律（pet/A100/未来任何服务器）。核心铁律：远程 = 只读执行环境，
  所有文件改动都在本地完成，经 git push 同步到远程；禁止把远程当开发机。
  触发场景：ssh 到任何项目服务器执行任何操作之前；本地改动需要同步到远程时；
  push 被拒绝时；在远程装环境/下载数据/动配置之前；与远程共享用户协作时。
  配套：remote-servers skill（连接方式/环境手册/硬件清单）。
metadata:
  default-enabled: true
---

# 远程服务器交互纪律

> **一条铁律**：远程服务器是**只读的执行环境**——代码、配置、脚本的一切改动都在**本地**完成并提交，然后 push 同步过去。远程上的每一个"临时修改"都是未来某次 push 失败和事故的种子。

## 0. 服务器信息登记表

**`servers.yaml`**（本 skill 目录下）是远程服务器的唯一信息源：连接方式（alias/主机/端口/账号/密码）、GPU 型号与数量、conda 环境清单、存储位置、当前状态与坑位记录。

- **每个会话操作远程前先读它**——不了解服务器现状就动手，是事故的第一大来源
- **服务器变更（新机器/新环境/IP 变化/降级）后必须更新它**
- 安全须知见文件头（明文密码随仓库管理的风险提示）

## 1. 标准工作闭环（唯一的正确方式）

```
本地改文件 → git commit → git push pet main（updateInstead 自动刷新远程工作树）
  → ssh 远程执行（训练/推理/测试）
  → 产物留在远程的 gitignore 目录 / scp 回本地
```

- push 前远程工作树**必须是干净的**（updateInstead 语义）
- push 后必须验证远程 HEAD：`ssh pet "cd repo && git log --oneline -1"`
- **禁止**：ssh 进去用 vim/sed/python 直接改文件；在远程 `git commit`（制造本地没有的分叉）；在远程 clone 第二份仓库当开发机

## 2. push 被拒的标准处置（不要发明新流程）

### 2a. "Working directory has unstaged changes"（远程工作树脏）
远程有人（用户/其他会话）改了文件。**那些改动不是垃圾，不能丢**：
```bash
ssh 远程 "cd repo && git stash push -q -m 'sync-<日期>'"
# 本地 push
git push pet main
ssh 远程 "cd repo && git stash pop"   # 恢复他人改动
```

### 2b. "Could not update working tree to new HEAD"（untracked 文件将被覆盖）
远程存在与 push 内容同路径的 untracked 文件：
```bash
ssh 远程 "cd repo && git ls-files --others --exclude-standard -z | tar --null -T - -cf /tmp/untracked_backup.tar"
ssh 远程 "cd repo && git clean -fdq"        # 备份后再清
# push
ssh 远程 "cd repo && tar -xf /tmp/untracked_backup.tar"   # 恢复（内容相同的文件自动归位）
```
- **必须用 `--null -T -` 处理 CJK 文件名**（普通分词会炸）
- 恢复后 `git status` 检查：变成 modified 的文件 = 远程版本与本地有差异，**向用户报告差异**，不要静默覆盖

### 2c. 非 fast-forward（远程有本地没有的提交）
先 `git fetch 远程 && git merge-base --is-ancestor 远程/main main` 判断；diverged 时**先把远程提交 fetch/merge 进本地**再推，禁止 force push。

## 3. 三阶段纪律同样约束远程操作

远程服务器上的以下动作 = **实施动作**，必须先有已批准的 change：
- 安装任何环境/包（conda env、pip install 到共享环境）
- 下载数据/权重
- 修改服务器配置、创建/删除服务
- clone 仓库到新机器（新服务器启用 = 一个 change）

纯只读操作不受限：nvidia-smi、看日志、读文件、git status/log。

## 4. 环境隔离纪律（共享机）

- **共享机的现有 conda 环境 = 别人的生产环境**。禁止往里装包/升级包（哪怕"只是加一个小的"——依赖解析可能连坐升级 numpy/torch）
- 新依赖需求 → **新建独立 env**（clone 现有 env 打底 + 增量安装，如 pet→plf）
- 装完必须验证原环境不受影响：`原环境 python -c "import 关键包; print(版本)"`
- 新机器启用（连 conda 都没有）→ 这是一个 change（见 provision-a100-server 先例）

## 5. GPU 使用纪律

- 任何 GPU 任务开跑前：`nvidia-smi --query-gpu=index,memory.used,utilization.gpu` 查占用
- 选空闲卡：`CUDA_VISIBLE_DEVICES=N` 显式指定，不裸跑
- 两卡都忙：等待或与用户/占用者协调；**禁止抢占**
- 长任务用 nohup + 日志文件，不用交互式占住终端

## 6. 脚本交接方式

- 本地写好脚本文件 → `scp` 到远程 `/tmp/`（一次性）或放 `scripts/` 入库（可复用）
- **禁止** ssh + heredoc + Python 三层引号嵌套（真实翻车案例：`unexpected EOF` + `UnboundLocalError` 连环）
- 脚本执行后**必须验证实际效果**（文件存在、行数、关键输出），不能只看脚本打印"成功"——真实案例：replace 打印成功但锚文本未匹配，文件根本没变

## 7. 连接问题

- ssh 连不上（动态 IP 服务器）→ `bash scripts/pet_repin.sh`（dig + 探活 + 改 ssh config）
- `kex_exchange_identification: Connection reset` → 网络抖动，等 30s 重试；连续失败才 repin
- 长命令超时：用 nohup 后台 + 日志轮询，不要拉长 ssh 超时硬等

## 8. 翻车案例存档（每个都是真实发生的）

| 事故 | 根因 | 修正 |
|---|---|---|
| A100 未经 change 批准就开始装环境/clone | 跳过三阶段 | AGENTS.md 三阶段纪律 + 违规披露写进 change |
| push 反复被脏工作树拒 | 远程直接改过文件 | stash/备份/clean 流程固化为本文档 2a/2b |
| tar 备份 CJK 文件名失败 | 分词炸引号 | `--null -T -` |
| ssh heredoc 语法错误 | 三层引号嵌套 | 脚本本地写好 scp |
| replace 打印成功但文件未变 | 无验证的习惯 | 写后必 grep/验证实际内容 |
| plf 装包首次静默失败 | `-q` 吞错误输出 | 远程 pip 安装不用 -q，或 tail 显示错误 |
