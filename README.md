# Pet Action Recognition

宠物动作识别研究项目——从文献调研、论文追踪到模型评测的全流程支撑平台。

## 项目背景

本项目聚焦于宠物（猫/狗）动作识别方向，核心挑战是**粗粒度与细粒度动作之间的性能鸿沟**：当前主流方法在粗粒度动作（行走、站立、奔跑）上已达 88%+ 准确率，但细粒度动作（如"反刍-躺卧" vs "反刍-站立"）仅 12.7%–29.6%。

研究覆盖以下技术路线：
- 2D CNN → 3D CNN → Transformer → Skeleton → 多模态 → 视频基础模型
- 级联架构：姿态提取 → 粗粒度分类 → 细粒度识别
- Stitching-Retargeting 范式：缝合个体表征 → 重定向动作识别能力
- 部件级时序建模（PMTNet 路径）

> 研究背景详见 [动作识别系列文章](https://gongshangzheng.github.io/action-recognition-hub.html)

## 项目结构

```
pet-action-recognition/
├── management/      # 项目管理体系（参考 InternWiki）
│   ├── team/        # 团队成员档案
│   ├── daily/       # 日报
│   ├── weekly/      # 周报
│   ├── monthly/     # 月报
│   └── docs/        # 项目管理文档
├── papers/          # 论文搜集体系（参考 SeekVerse）
│   ├── config/      # 数据源配置、分类规则
│   ├── data/        # 论文数据库（已 gitignore）
│   ├── cache/       # 抓取缓存（已 gitignore）
│   ├── scripts/     # 搜集与处理脚本
│   └── docs/        # 论文笔记与综述
├── evaluation/      # 动作识别模型评测
│   ├── models/      # 模型定义与实现
│   ├── datasets/    # 数据集加载与预处理
│   ├── configs/     # 评测实验配置
│   ├── scripts/     # 训练与评测脚本
│   └── results/     # 评测结果（已 gitignore）
└── docs/            # 其他相关文档
```

## 各模块说明

### `management/` — 项目管理

参考 InternWiki 的多人协作文档体系，建立结构化的项目管理机制：

- **团队成员**：成员档案、研究方向、技能特长
- **日报 / 周报 / 月报**：记录研究进展、实验结果与阶段性总结
- **管理文档**：任务规划、里程碑、会议纪要等

### `papers/` — 论文搜集

参考 [SeekVerse（寻章）](https://github.com/user/SeekVerse) 的自动化论文搜集体系，构建面向动作识别领域的论文追踪系统：

- **多源聚合**：arXiv、Semantic Scholar、OpenAlex 等
- **智能分类**：按技术路线（2D CNN / 3D CNN / Transformer / Skeleton / VFM / 多模态）自动分类
- **论文笔记**：精读笔记、综述整理

重点关注的会议/期刊：CVPR、ICCV、ECCV、NeurIPS、ICML、Nature Communications、IJCV、Animals

### `evaluation/` — 模型评测

存放动作识别模型的评测代码，覆盖以下模型族：

| 模型 | 类型 | 备注 |
|------|------|------|
| SlowFast | 3D CNN 双路径 | 粗粒度基线 |
| I3D | 3D CNN | 经典基线 |
| VideoMamba | SSM | 边缘部署候选（74M） |
| SkeleTR | 骨架 Transformer | 细粒度识别 |
| PMTNet | 部件级时序 | 猫行为专用（93.1%） |
| InternVideo2 | VFM | 6B 参数，SOTA |

主要评测数据集：Animal Kingdom、MammalNet、CVB、PBRD

### `docs/` — 其他文档

存放不属于以上模块的相关文档，包括：
- 技术调研报告
- 方案设计文档
- 工具链使用指南
- 会议/比赛相关记录

## Claude Code Skills

本项目提供配套的 Claude Code skills，可自动触发使用指南：

| Skill | 功能 |
|-------|------|
| `pet-action-recognition-web` | Web 全栈开发、服务启动、调试 |
| `pet-action-recognition-management` | 项目树、团队、报表、任务看板、里程碑、会议纪要 |
| `pet-action-recognition-papers` | 论文导入、分类、笔记、搜索筛选 |
| `pet-action-recognition-evaluation` | 模型、数据集、评测配置、运行、结果对比 |

当你在项目中使用 Claude Code 时，相关 skills 会自动加载，提供操作指导。

## 快速开始

```bash
# 克隆仓库
git clone <repo-url>
cd pet-action-recognition

# 各模块独立使用，详见各子目录说明
```

## 相关资源

- [动作识别系列文章](https://gongshangzheng.github.io/action-recognition-hub.html)
- [DeepLabCut](https://github.com/DeepLabCut/DeepLabCut) — 多动物姿态估计
- [SuperAnimal](https://www.nature.com/articles/s41467-024-48792-2) — 跨物种零样本姿态估计
- [MMAction2](https://github.com/open-mmlab/mmaction2) — 视频理解工具箱
- [Animal Kingdom Dataset](https://github.com/sutdcv/Animal-Kingdom) — CVPR 2022 动物行为数据集

## License

MIT
