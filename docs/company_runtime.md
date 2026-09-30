# 公司服务器训练与前向环境

工作目录：`/home/work/analysis_code`，计算节点：`work@10.33.37.211`。

本次只安装依赖并检查导入、命令入口和配置。没有构建模型、下载权重、
运行前向/反向、训练或评估，也没有处理公司数据集。

2026-09-30 已完成安装：69 项检查没有未解决的失败，32 份配置文件解析通过
（含配置包初始化文件），4 张 A30 可见，MMCV 编译扩展导入正常。
审计状态为 `passed_with_packaging_warning`，Decord 的包标签提示详见下文。
已修正 LFB 注册项原有的 `8xb16` 文件名错误，使其指向实际存在的 `8xb12` 配置。

## 使用环境

```bash
cd /home/work/analysis_code
source .runtime/pet/bin/activate
python --version
```

也可直接使用 `/home/work/analysis_code/.runtime/pet/bin/python`。
不要使用系统的 Python 2.7。系统 Python 和 NVIDIA 驱动均保持原状。

入口是 `scripts/train_model.py`、`scripts/inference.py`、`scripts/run_test.py`；
对应底层入口为 `models/mmaction2/tools/train.py`、`tools/test.py`。
查看 `--help` 不会启动训练或前向。等待数据集准备好后，需明确视频目录、
train/val/test 标注、类别数、类别名称和使用的 checkpoint，再实际验证流程。
传入 checkpoint 时推荐绝对路径，避免旧包装脚本对相对路径的转换。

现有 `configs/cats_*`、`configs/pet_mammal_*` 保留原研究数据集设定，
不会自动转换成公司的数据集。部分上游模型配置只有测试段，需要选择项目
已有训练模板或补齐训练配置。骨架模型另需关键点标注/提取流程。

## 版本和证据

关键版本：Python 3.10、torch 2.1.2 / CUDA 12.1、torchvision 0.16.2、
MMCV 2.1.0、MMEngine 0.10.7、本地 MMAction2 1.2.0、NumPy 1.26.4。
完整固定清单在 `configs/company_runtime_requirements.txt`；以服务器实际
`pip-freeze.txt`、`packages.json` 为最终安装记录。

安装与审计文件：`results/deployment/company_runtime_20260930/`：

- `install.log`、`install_v3.log`：分阶段安装和重试记录。
- `audit_final.log`：修正 LFB 引用后的最终检查记录；以 `runtime_audit.json` 为准。
- `runtime_audit.json`：逐项环境检查，明确记录未执行模型。
- `pip-check.txt`、`pip-freeze.txt`、`packages.json`：一致性与版本信息。
- `wheels.sha256`：保留安装包的哈希清单。
- `*.help.txt`、`ffmpeg-version.txt`：命令入口及编码工具检查。

Decord 0.6.0 官方 `py3` wheel 内部错误标注为 `cp36`，新版 pip check 会报告
平台不支持。本机已确认该包及其 ctypes 原生库能在 Python 3.10 导入。
审计仅在原始输出恰好只有这一项、元数据符合已知问题且导入成功时记录为
`passed_with_packaging_warning`，不会忽略其他依赖冲突；视频解码尚未执行。

审计通过不代表已验证模型数值、显存需求、真实视频解码或数据标签正确性。
实际训练、前向和评估留待数据准备完成并获准执行后进行。

## 下载缓存与恢复

- `.runtime/conda/`：Python 引导环境。
- `.runtime/pet/`：项目依赖环境。
- `.runtime/cache/bootstrap/`：已校验 SHA256 的 Miniconda 安装器。
- `.runtime/cache/wheels/`：核心依赖和 CUDA/MMCV 二进制安装包。
- `.runtime/cache/pip/`：pip 下载缓存。

安装工具为 `scripts/install_company_runtime.sh`。它可以重试联网安装，
并在依赖装完后自动做环境审计，不会运行模型。下载失败时查看日志后重试，
不要删除缓存。传输 Bash 脚本需保留 LF 换行。

网络关闭后，在已激活的项目 Python 环境中，可从保留的包恢复依赖：

```bash
python -m pip install --no-index --find-links .runtime/cache/wheels \
  -r configs/company_runtime_requirements.txt \
  mmcv==2.1.0 moviepy==1.0.3 pytorchvideo==0.1.5 lmdb==1.5.1
python -m pip install --no-index --no-deps --no-build-isolation -e models/mmaction2
python scripts/audit_company_runtime.py --root /home/work/analysis_code \
  --out /home/work/analysis_code/results/deployment/company_runtime_20260930
```

这套环境覆盖动作识别训练/推理/评估及注册的 AVA 动作检测依赖。
GroundingDINO、BoxMOT、姿态提取、VLM 云 API 和 RV1126B/RKNN 工具链是
不同的可选流程，不应直接视作已在本环境中验证或已准备离线权重。
