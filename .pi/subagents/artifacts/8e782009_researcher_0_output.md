调研完成。已写入 `/Users/zhengxinyu/pet-action-recognition/.pi/subagents/artifacts/outputs/8e782009/research.md`，共 **25 篇**论文，全部为真实存在、发表于顶刊/顶会（Nature Methods、Neuron、eLife、CVPR/ICCV/NeurIPS 等）的文献。

**清单结构**（按价值分组）：
- **奠基经典**（2013–2018）：JAABA、MotionMapper、MoSeq、DeepLabCut、Who Let the Dogs Out（狗行为识别）
- **姿态工具与 3D**（2020–2022）：SLEAP、DANNCE、AniPose、OpenMonkeyStudio、SuperAnimal
- **基准数据集**：AP-10K、APT-36K、Animal Kingdom、MammalNet、OpenMonkeyChallenge、AnimalWeb、ATRW（Re-ID）
- **行为/动作识别方法**：MARS、B-SOiD、A-SOiD、VAME、DeepEthogram、LabGym、AmadeusGPT、Keypoint-MoSeq

**重要说明（局限）**：本环境未提供 `web_search` 工具，清单基于我对该领域文献的知识整理。论文本身的真实性置信度高；但部分 arXiv ID 与出版商 URL 的具体编号来自记忆，其中高置信度的 arXiv ID 已给出（AP-10K 2108.12617、Animal Kingdom 2204.08129、APT-36K 2210.02319、VAME 2005.08981、AmadeusGPT 2307.04858、Keypoint-MoSeq 2303.15036、MammalNet 2306.00576、Ehsani 1803.10827），不确定的一律置空。SuperAnimal、A-SOiD、B-SOiD、SLEAP 等的出版商文章号建议入库前用 arXiv API 或 Crossref 抽查一次。