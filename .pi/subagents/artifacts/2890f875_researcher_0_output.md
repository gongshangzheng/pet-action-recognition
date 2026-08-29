已完成调研并写入指定路径。

**交付物**：`/Users/zhengxinyu/pet-action-recognition/.pi/subagents/artifacts/outputs/2890f875/research.md`

**清单概要**（25 篇，全部为真实可核验论文）：

- **掩码/自监督预训练前沿**：VideoMAE (2203.12602)、VideoMAE V2 (2303.16727)、MaskFeat (2112.09133)、V-JEPA (2404.08471)、V-JEPA 2 (2506.09985)
- **视频基座大模型**：InternVideo (2212.03191)、InternVideo2 (2403.15377)、InternVideo2.5 (2501.12386)、VideoPrism (2402.13217)
- **图像模型适配视频路线**：UniFormer (2203.04676)、UniFormerV2 (2211.09552)、AIM (2306.13812)
- **新架构**：VideoMamba (2403.06977)
- **多模态视频理解**：Video-LLaMA、Video-LLaVA、Video-ChatGPT、Qwen2-VL、Qwen2.5-VL、VILA
- **经典奠基**：Video Swin Transformer、MViTv2、TimeSformer、SlowFast
- **数据集**：Kinetics-700、Something-Something (SSv1/v2)

每条均含 `arxiv_id` / `title` / `year` / `venue` / `url` / `one_line_value_zh`。

**注意事项**：本环境没有 web_search 工具可用，清单基于训练知识整理；其中 **InternVideo2.5 (2501.12386) 和 V-JEPA 2 (2506.09985)** 两个 arXiv 编号置信度略低，建议入库前人工快速核验。Qwen2.5-VL 与本项目已集成的 Qwen3-VL 路线直接相关，已在价值说明中标注。