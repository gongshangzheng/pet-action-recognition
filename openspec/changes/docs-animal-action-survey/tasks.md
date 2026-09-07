# Tasks: docs-animal-action-survey

## 1. 综述文档撰写

- [ ] 1.1 撰写 `papers/docs/animal-action-survey.md`，结构：
  - §1 引言：领域定义、与本平台的关系、阅读方法
  - §2 动物动作识别发展脉络：行为学工具时代（JAABA/MotionMapper/MoSeq）→ 深度学习姿态驱动（DeepLabCut/SLEAP/MARS/B-SOiD/A-SOiD）→ 视频像素路线（DeepEthogram/LabGym→Animal Kingdom/MammalNet 基准时代）→ 基础模型时代（SuperAnimal/AnimalMotionCLIP/BehaviorVLM/AmadeusGPT）
  - §3 宠物/家养动物子领域：DECADE 起点 → 公开基准盘点（Animal Kingdom/APT-36K/AP-10K/MammalNet/CVB/MammAlps/KABR）→ 空白分析（pet action recognition 检索为空 = 平台机会）
  - §4 最新方法专讲（2024–2026）：DiffPose-Animal、AP-CAP、MamKPD、Promptable Animal Pose Tracking、AnimalMotionCLIP、Keypoint-MoSeq、A-SOiD、AmadeusGPT、BehaviorVLM、FSAR 综述/Task-Adapter/Trokens、V-JEPA 2/VideoMamba/MS-Temba 等，每篇含动机/方法/对本项目启示
  - §5 两大核心问题证据链：数据稀缺对策对比表（自监督续训/Adapter/姿态桥接/few-shot/合成）+ 人→动物迁移证据表（6 篇）
  - §6 阅读地图：必读 10 篇 → 按角色（训练/评测/数据/live）的深入路径
  - §7 附录：与论文库/核心清单/research-verified.json 的交叉引用、已知缺口
- [ ] 1.2 全文 arXiv ID 与论文库核对一致（引用必须来自已核验条目）
- [ ] 1.3 `research-landscape.md` 头部加交叉链接（概览版 ↔ 综述版）

## 2. 收尾

- [ ] 2.1 向用户口头汇报综述核心内容（领域脉络 + 最新方法 + 结论）
- [ ] 2.2 提交（docs: 前缀）
