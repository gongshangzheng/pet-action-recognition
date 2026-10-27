## 正式入口

本目录顶层保留训练、推理、评测、数据准备及分析命令。模型正式测试入口仍是
`scripts/run_test.py`，它属于模型评测，不属于项目自动化测试。

猫动作数据与实验入口为 `prepare_cat_action_v1.py`、`run_cat_action_v1.py`、
`run_cat_action_batch.py`；数据读取与指标扩展在 `petlib/datasets/cat_intervals.py`。
实验协议、成绩及局限见 [训练说明](../docs/cat_action_training_v1.md)。

## 自动化测试

项目测试统一在 `tests/`，测试夹具写入 `results/tests/` 后清理。数据准备、
归档恢复与链接安全测试只使用合成小样本，不启动模型或 GPU。

```bash
python3 -B -m unittest discover -s tests -v
```

## 预检与烟测

`scripts/checks/` 包含环境审计、模型前后向预检、区间采帧检查、模拟器检查、
部署清单校验和烟测产物核验。模型预检仅在远程相应环境执行。

```bash
python scripts/checks/check_cat_action_models.py --help
python scripts/checks/check_cat_action_v1.py
python scripts/checks/verify_cat_interval_smoke.py
```

`check_rv1126b_simulator.py` 是只在 RAM 中生成模型的专用无落盘检查，保留
`/dev/shm` 工作区；它不属于自动化测试夹具，不生成持久分析产物。

## 部署与迁移

`scripts/migration/` 收纳代码打包/部署、环境准备、离线资源缓存、课题组迁移及
代码同步工具。`*_lab_*` 工具保留原迁移目标 `/home/wyy/pet-final` 和相应连接
配置，作为显式运维命令；本次整合没有运行它们或安装环境。

## 既有权重软链接

清单 `configs/cat_action_v1_checkpoints.json` 固定六模型最佳权重的配置对应及
完整 SHA-256。只在 pet 上运行以下命令：

```bash
python3 scripts/migration/link_cat_action_checkpoints.py
python3 scripts/migration/link_cat_action_checkpoints.py --apply
```

第一条仅验证，第二条创建 `checkpoints/cat_action_v1/<model>/best.pth`，指向
`/home/wyy/pet-final/results/training/cat_action_v1/<model>/work/` 中的最佳文件。
链接工具先检查整批源文件哈希，拒绝覆盖现存文件、不同链接及目录软链接，
重复运行可复用同目标链接。结果写入 `results/migration/cat_action_v1_links.json`。

权重链接不迁移训练日志、数据索引或运行环境，也不自动注册 Web 训练 run。
在 mac 上不创建这些机器绝对路径链接；使用模型时仍须提供对应配置和七类映射。

## 路径维护

移动入口后，代码及当前操作说明同步更新；OpenSpec 来源记录、旧日志和实验
说明中的历史命令保留原始路径。新的调用方式以本页和实际目录为准。
