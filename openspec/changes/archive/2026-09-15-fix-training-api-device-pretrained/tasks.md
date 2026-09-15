# fix-training-api-device-pretrained Tasks

## 1. CLI 修复

- [x] 1.1 `scripts/train_model.py`：`--device` 去掉 `choices=["cuda","cpu"]`，加正则校验 `^(cpu|cuda(:\d+)?)$`；`cuda:N` 时在构建子进程 env 处注入 `CUDA_VISIBLE_DEVICES=N`（cpu 分支原有 `CUDA_VISIBLE_DEVICES=""` 保持）
- [x] 1.2 `scripts/train_model.py`：`--pretrained` 从 `store_true` 改为带值参数（`metavar="URL_OR_PATH"`）；`build` cfg-options 处 `load_from={args.pretrained}` 直接使用其字符串值；裸 `-p` 由 argparse 自然报错
- [x] 1.3 `scripts/run_test.py`：`--device` 同 1.1 方案放开 `cuda:N`（含 benchmark 内部 `dev` 取值适配）

## 2. 验证（本地 argparse 级，不占 GPU）

- [x] 2.1 `--device cuda:1` / `--device cuda` / `--device cpu` / `--device gpu0`（应报错）四种取值解析符合预期
- [x] 2.2 `--pretrained=<url>` 生成的训练命令含 `load_from=<url>`；裸 `-p` 报错；`-p` 与 `-l` 同传报互斥错误
- [x] 2.3 用不存在 config 触发到 `[cmd]` 打印即止，确认命令行参数正确组装（不实际训练）

> 注：本地 macOS 因 OpenMP 重复加载（torch 环境冲突）无法跑 argparse 验证，2.x 改在 pet 上完成（目标环境即 pet）

## 3. pet 同步与实测

- [x] 3.1 rsync 两个修复文件到 pet（工作区脏、push 被阻塞，文件级同步；同步前确认 pet 侧两文件与本地修复前版本 md5 一致）
- [x] 3.2 pet 上经 API 发起一次真实训练（`device: cuda:N` + `pretrained: true`，选一个轻量模型 1 epoch）确认 run 进入 running 且正常推进；注意避开正在运行的 cats 批量任务占用的卡
- [x] 3.3 实测通过后 commit（`fix: 训练/测试 CLI 支持 cuda:N 选卡 + pretrained 带值传参`）并同步 tasks.json 勾选状态

## 4. 收尾

- [x] 4.1 更新 testing/training skill 中 `--device` 用法描述（检查后无需改动——skill 文档原本就按目标行为写的，此次是代码对齐文档）
- [x] 4.2 清理验证产生的 dry/probe run 记录
- [ ] 4.3 `openspec archive` 归档本 change
