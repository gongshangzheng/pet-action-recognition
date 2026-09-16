调研完成。以下为结构化简报，每条结论均标注出处（文件:行号 / 章节）。

---

# 猫本体抠像选型精读简报：SAM2 vs RVM vs BiRefNet

**材料版本（本地快照，`third-party/refs/repos`）**
- sam2: commit `2b90b9f` (2024-12-15)，Paper v2 (arXiv 2408.00714v2)
- rvm: commit `53d74c6` (2023-03-13)，Paper v1 (arXiv 2108.11515v1)
- birefnet: commit `ebcc0bc` (2026-09-02)，Paper v7 (arXiv 2401.03407v7)

---

## 1. 输入要求与输出形式

### 1.1 SAM2 —— 需要 prompt（box 可用），输出**二值 mask**，非 alpha

| 项 | 结论 | 出处 |
|---|---|---|
| prompt 类型 | 点 / **框** / mask，任意帧 | 论文 §3 行47：*"takes as input points, boxes, or masks on any frame of the video"* |
| box 训练支持 | 是，训练时 25% 概率用 bbox 作初始 prompt | 论文 §4 Training 行281：*"a bounding box input with probability 0.25"* |
| box 实测精度 | 17 个零样本视频数据集上 box prompt J&F = **74.4**（1click 64.7 / 5click 77.6 / GT mask 79.3） | 论文 Table 4 行471–476 |
| 视频传播 API | `init_state()` → `add_new_points_or_box()` → `propagate_in_video()` 逐帧 yield | `sam2/sam2_video_predictor.py:42-45, 161, 546-630` |
| box 在视频中的实现 | box 展开为 label(2,3) 的两个点；**box 必须先于任何点 prompt** | `sam2/sam2_video_predictor.py:195-210`（错误信息在 198-203） |
| 输出形式 | 每帧 mask **logits**（float），阈值 `>0` 得二值 mask；demo 代码 `score_thresh=0` | `sam2/sam2_video_predictor.py:627`（yield video_res_masks）；`demo/backend/server/inference/predictor.py:49, 144` |
| **是否有 alpha** | **无**。全仓无 matting/alpha 头（`grep -ri alpha` 仅命中 sav 评测的 RGBA 容器与 loss 超参） | sam2 仓库全文检索 |
| 输入分辨率 | 统一 resize 到 1024×1024（方形） | `sam2/configs/sam2.1/sam2.1_hiera_l.yaml:89`；`sam2/utils/misc.py:172-210` |
| 视频读取 | 支持 `.mp4` 文件或 JPG 帧目录两种 | `sam2/utils/misc.py:185-210` |
| 附带输出 | 有**遮挡/在场**预测头（object 是否在当前帧可见） | 论文 §4 行251、附录 D.1 行873-877 |

### 1.2 RVM —— **不需要 trimap**，输出 **alpha + foreground**，训练域=人物

| 项 | 结论 | 出处 |
|---|---|---|
| 辅助输入 | **不需要** trimap / 预拍背景 | 论文 Abstract 行31-32：*"does not require any auxiliary inputs such as a trimap or a pre-captured background image"* |
| 输出 | `fgr` (3ch, RGB) + `pha` (1ch, alpha)，均归一化到 0~1 | `model/model.py:56-71`；`documentation/inference.md:96-102` |
| 输出语义 | 真 **alpha matte**（软边）+ 前景色，即 I=αF+(1−α)B | 论文 行42-45（公式 1） |
| 是否需要时序状态 | **必须**顺序喂帧并回传 4 路 recurrent states；不回传即等于逐帧图像模型 | `documentation/inference.md:43-66`（"Correct Way"/"Wrong Way" 对照） |
| 训练域 | **人类**。matting 只用 "only images of humans"（行201）；分割只用 "clips containing humans"（行227）、"only trained on the human category"（行262） | 论文 §4.1/§4.2/§4.4 |
| downsample_ratio | 需按分辨率手调，使下采样后落在 256–512 px | `documentation/inference.md:22-33` |

### 1.3 BiRefNet —— 无 prompt（box 可选引导），输出单通道 **0~1 显著性图（近似软 mask）**，**逐帧**

| 项 | 结论 | 出处 |
|---|---|---|
| 输入 | 单张图像，统一 resize 到 1024×1024 | 论文 §4.3 行426；`utils.py:11` |
| prompt | 训练/推理**不需要** prompt（DIS 任务）；另有可选 box-guided 版本 | 论文 §1/§3；README "Segmentation with box guidance" 段 |
| 输出 | `model(x)[-1].sigmoid()` → 单通道 0~1 图，再双线性插值回原图尺寸 | `inference.py:35-46` |
| **是否逐帧** | **是**。官方视频 notebook 的做法是「抽帧 → 逐帧独立前向 → 逐帧写回」，**无任何时序状态/帧间后处理** | `tutorials/BiRefNet_inference_video.ipynb` cell 4（`for idx in range(...)` 循环，无 rec/smoothing） |
| 任务定义 | DIS（dichotomous image segmentation，前景/背景二分）；类别无关 | 论文 Abstract 行33；§3.1 |
| 是否 alpha | 是「软 mask/显著性图」，语义上接近 alpha；另有专门 matting 权重（BiRefNet-matting / HR-matting） | README Model Zoo "general matting"/"portrait matting" |

> **对 `pet-background-removal` spec（二值掩码 + 背景置黑）的适配性**：SAM2 天然产出二值 mask；RVM 产出 alpha（需阈值化）；BiRefNet 产出软图（需阈值化）。三者都需要自己做「阈值/膨胀 + 置黑合成」。

---

## 2. 速度对比（论文/官方报告值）

| 模型 | 报告 FPS / 延迟 | 硬件 | 分辨率 | 出处 |
|---|---|---|---|---|
| SAM2 (Hiera-B+) | **43.8 FPS** | A100, batch=1 | 1024² | 论文 §7 行508-509 |
| SAM2 (Hiera-L) | **30.2 FPS** | A100, batch=1 | 1024² | 同上 |
| SAM2 图像任务 | 130.1 FPS（batch=10） | A100 | 1024² | 论文 Table 5 行517；§D.3 行1070 |
| SAM2.1 (官方 README, VOS) | tiny 91.2 / small 84.8 / **base+ 64.1** / **large 39.5** FPS | A100, torch2.5.1/cuda12.4 | — | sam2 `README.md:167-170, 173` |
| SAM2 全模型 compile 优化 | "major speedup"（未给绝对值） | — | — | `RELEASE_NOTES.md:3-8`；`sam2/build_sam.py:107,113`（`vos_optimized=True`） |
| RVM (mobilenetv3) | **HD 104 FPS / 4K 76 FPS** | GTX 1080Ti FP32 | 1920×1080 / 3840×2160 | 论文 行20；Table 4 行385-395 |
| RVM 官方速度表 | RTX3090 FP16: HD **172 FPS** / 4K 154 FPS；RTX2060S: 134/108 | 见左 | 同左 | rvm `README.md:213-221` |
| BiRefNet (SwinL) | **83.3 ms** ≈ 12 FPS | A100 | 1024² | 论文 Table 7 行671 |
| BiRefNet 轻量 | SwinT 40.9ms；PVTv2-b0 32.9ms | A100 | 1024² | 论文 Table 7 行671-679 |
| BiRefNet 官方 4090 实测 | FP16 **57.7 ms ≈ 17 FPS**，显存 3.5 GB | RTX 4090 | 1024² | birefnet `README.md` Model efficiency 段 |
| BiRefNet 文字结论 | *"FPS of the largest BiRefNet can be more than 10"* | A100 | 1024² | 论文 §4.4 行711 |

**对「批处理数千段视频」的含义**

- 语料规模（本地 OpenSpec 记录，非论文）：followcam 34 段但**总素材仅 14.7 分钟**（`openspec/changes/batch-followcam-extraction/tasks.md:11`）；mammal_v0 **~3 小时**（`archive/2026-09-16-docs-repo-inventory/design.md:97`）；cats v1 clip_length 4s × 717 段 ≈ **48 分钟**（`archive/2026-09-15-cats-dataset-v1/specs/datasets/quadruped-cats-v1/spec.md:69`）。合计 **≈ 4 小时视频**。
- **推算（非论文数据，仅供量级参考）**：4h @30fps ≈ **43 万帧**。
  - SAM2 base+ 按 64 FPS 计 ≈ **1.9 h** GPU 时间；large 按 39.5 FPS ≈ **3 h**。
  - BiRefNet SwinL 按 17 FPS（4090）≈ **7 h**；轻量 SwinT 更快但精度下降。
  - RVM mobilenetv3 按 ≥104 FPS 计 ≲ 1.2 h（4090 上应更快）。
- **结论**：纯吞吐排序 **RVM > SAM2 ≈ BiRefNet（轻量）> BiRefNet（SwinL）**。但 RVM 需顺序喂帧，**无法按帧并行**（`documentation/inference.md:43-66`），且用 `seq_chunk` 提并行度（`inference.py:36`）。SAM2 也是流式顺序（`sam2/sam2_video_predictor.py:583`），但可用 `offload_video_to_cpu/offload_state_to_cpu` 降显存、`vos_optimized=True` 提速（代价：数值差异）。

---

## 3. 时序一致性（帧间闪烁）

| 机制 | 结论 | 出处 |
|---|---|---|
| **SAM2：memory attention + memory bank** | 当前帧特征 cross-attend 到 memory bank（最近 N 帧的 FIFO + M 个 prompted 帧 + object pointers），并有 2D RoPE 编码短时运动 | 论文 §4 行233-240；**memory bank 定义行260-266**；附录 D.1 行865-871 |
| SAM2 长时失效场景 | 镜头切换、拥挤、**长时遮挡**、超长视频会丢失/混淆目标；需中途补 prompt 恢复 | 论文 Limitations §C 行835-839 |
| **RVM：ConvGRU 递归（论文题目的 "Temporal Guidance"）** | 多尺度 ConvGRU 递归解码器 + **显式 temporal coherence loss (dtSSD)**；论文用 **dtSSD** 量化闪烁 | 论文 §3.2 行166-195；temporal loss 行311-313；dtSSD 定义行307 |
| RVM 时序效果 | 与 MODNet 对比：MODNet 在扶手处 flicker，RVM 一致（Fig.5）；平均 alpha MAD 随帧数下降并稳定 | 论文 行442-458, 图4/图5 |
| RVM 消融 | 去掉递归（Ours No Recurrence）质量/一致性变差 | 图4 行~450 |
| **BiRefNet** | **无时序机制**。论文全文无 temporal/video 方法（只提第三方把它做成视频工具） | 论文检索 `video|temporal` 仅命中行736/739/789 的第三方描述 |
| 官方对比 | BiRefNet README 引用的第三方（Toyxyz）已把 BiRefNet 与 **Robust Video Matting** 在视频上做过对比 | 论文 行739；birefnet `README.md` News 段 |

**排序：RVM（有 dtSSD 专项优化 + 递归记忆）≈ SAM2（memory attention）>> BiRefNet（逐帧，无机制）**

补充取舍：
- 消除**闪烁**（帧间抖动）——RVM 是唯一有**显式去闪烁损失**的（论文 行311-313），理论最优；
- 消除**漂移/身份错跟**（猫移动中 mask 跑到背景）——SAM2 的 memory attention + 遮挡头 + 可中途补 prompt 更强（论文 行835-839、行873-877）；
- BiRefNet 逐帧 → 帧间无约束，**必然闪**（尤其毛发边缘二值化抖动），且官方 notebook 未做任何平滑（`BiRefNet_inference_video.ipynb` cell 4）。

---

## 4. 动物 / 毛发泛化

| 模型 | 证据 | 结论 |
|---|---|---|
| **SAM2** | ① 数据引擎**不设类别约束**，目标是"任何有明确边界的物体"（论文 行287-289、行70）；② SA-V 挑战项含小物体、遮挡后重现（行73-74）；③ 零样本评测集含**野生动物**：*"Lindenthal Camera … wildlife park with segments around observed animals such as birds and mammals"*（行1210）；④ 训练混合了开放世界分布 + 视频（行517 Table 5 的 "our mix" 在 14 个视频零样本集达 69.6 mIoU） | **零样本对象泛化最强**，明确覆盖动物（鸟类/哺乳类）。**但对本项目的"猫"无专门评测数字——论文未说明** |
| SAM2 已知弱点（对猫直接相关） | *"SAM 2 also struggles with accurately tracking objects with very thin or fine details especially when they are fast-moving"*（行839） | **猫须/细毛 + 快速运动的猫**是公认弱项；猫胡须、尾部细结构可能丢 |
| **RVM** | 训练数据全部限定人类（行201/227/262）；模型定位 *"specifically designed for robust human video matting"*（README:29）；论文自述 *"our network must learn to semantically understand the scene and be robust in locating the human subjects"*（行232-233） | **对猫不可靠**：论文/代码**均未说明**对非人类（动物）的效果；"毛发细节"证据（行399 *"hair strands"*）指**人发**。存在把猫当背景直接抹掉的风险 |
| RVM 其他局限 | *"prefers videos with clear target subjects"*，背景有人会让目标歧义（行522-527） | 家庭多猫/人场景可能歧义 |
| **BiRefNet** | ① DIS 任务**类别无关**（Abstract 行33、§2.1 行72-73）；② 在 **COD（伪装物体检测）** 上 SOTA，论文举例含**青蛙**（行695 *"the occluded frog"*），COD 数据集普遍含动物；③ 官网 general-use 权重训练集含 DIS5K/DUTS/HRSOD/P3M/Human 等 | **倾向类无关**，且能分割"极细结构"，论文声称 *"segment thin threads at the hair level"*（行745-746）。**但对猫无任何专门评测——论文未说明**；且 DIS5K/HRSOD/COD 与"室内猫"域差异未验证 |

**小结（毛发边缘锐度）**：BiRefNet 论文自称 hair-level（行745-746）> RVM（人发，行399）> SAM2（细/快运动弱，行839）。但注意 BiRefNet 是**软图**，做二值化后边缘优势会部分消失。

---

## 5. 代码可运行性（依赖 / 权重下载 / 许可证 / 最小调用）

### 5.1 依赖

| 模型 | 依赖 | 出处 |
|---|---|---|
| SAM2 | python≥3.10，`torch>=2.5.1, torchvision>=0.20.1`，hydra-core, iopath, pillow；可选 CUDA 扩展（可跳过） | `sam2/setup.py:25-32`；`README.md:44-52`；`INSTALL.md` |
| RVM | `av==8.0.3, torch==1.9.0, torchvision==0.10.0, tqdm, pims`（**版本很旧，与新环境冲突风险高**） | `rvm/requirements_inference.txt` |
| BiRefNet | `torch>=2.5.0, torchvision, numpy<2, opencv-python, timm, scipy, scikit-image, kornia, einops, huggingface-hub, accelerate` | `birefnet/requirements.txt` |

### 5.2 权重下载 & 镜像可达性（**本机实测 2026-09-16，HTTP range 请求**）

| 模型 | 主源 | 实测 | 镜像 |
|---|---|---|---|
| SAM2 | `dl.fbaipublicfiles.com/.../sam2.1_hiera_*.pt`（4 个） | **http=206 可取**（`sam2/checkpoints/download_ckpts.sh`） | HF `facebook/sam2.1-hiera-large`（license apache-2.0）✅ |
| RVM | GitHub Releases `PeterL1n/RobustVideoMatting/releases/download/v1.0.0/*.pth`（+onnx/torchscript/tf/mlmodel） | **http=206 可取** | 无官方 HF 镜像；TorchHub 也走 GitHub（`hubconf.py:19-28`） |
| BiRefNet | HF `ZhengPeng7/BiRefNet`（`hf-mirror.com` 实测 **http=206**）；备选 GDrive | ✅ | 镜像可达 |

> 注：以上为**本机 macOS** 探测结果，pet 服务器网络需另测（`pet-background-removal` design 也把"权重不可得则回退候选"列为风险）。

### 5.3 许可证

| 模型 | 许可证 | 出处 |
|---|---|---|
| SAM2 | **Apache 2.0**（代码 + 权重 + demo + 训练） | `sam2/LICENSE:1`；`README.md:198` |
| RVM | **GPL-3.0**（⚠️ 传染性 copyleft） | `rvm/LICENSE:1-3`；`README.md:19` |
| BiRefNet | **MIT**（代码）；HF 权重 `license: mit` | `birefnet/LICENSE:1`；HF API `cardData.license=mit` |

**风险**：RVM 的 GPL-3.0 若与项目代码链接/分发，可能要求开源整个衍生作品。SAM2/BiRefNet 无此问题。

### 5.4 最小调用示例（关键函数/文件）

**SAM2（视频，box prompt）** — `README.md:104-124`
```python
from sam2.build_sam import build_sam2_video_predictor
predictor = build_sam2_video_predictor(model_cfg, checkpoint)   # 可加 vos_optimized=True
state = predictor.init_state(<mp4 或 jpg 帧目录>, offload_video_to_cpu=True)
predictor.add_new_points_or_box(state, frame_idx=0, obj_id=1, box=np.array([x1,y1,x2,y2]))
for frame_idx, obj_ids, mask_logits in predictor.propagate_in_video(state):
    mask = (mask_logits[0] > 0.0)   # 二值 mask，原视频分辨率
```
关键文件：`sam2/sam2_video_predictor.py:42,161,546`；`sam2/build_sam.py:107`

**RVM（顺序帧循环）** — `documentation/inference.md:82-95`
```python
from model.model import MattingNetwork
model = MattingNetwork('mobilenetv3').eval().cuda()
model.load_state_dict(torch.load('rvm_mobilenetv3.pth'))
rec = [None]*4
for src in YOUR_VIDEO:                      # [B,C,H,W] 或 [B,T,C,H,W]
    fgr, pha, *rec = model(src, *rec, downsample_ratio=0.25)
```
关键文件：`rvm/model/model.py:40-73`；`rvm/inference.py:24`（`convert_video`）

**BiRefNet（逐帧）** — `README.md:82-86`；`inference.py:35-46`
```python
from models.birefnet import BiRefNet           # 或 transformers AutoModelForImageSegmentation
m = BiRefNet.from_pretrained('zhengpeng7/BiRefNet').eval().cuda()
scaled = m(x)[-1].sigmoid()                    # 单通道 0~1，再插值回原尺寸
```
视频做法见 `tutorials/BiRefNet_inference_video.ipynb`（抽帧→逐帧→写回，无时序）

---

## 6. 综合推荐

### 推荐：**SAM2 为主（Hiera-B+ / B+ 或 L），RVM 仅作对照，BiRefNet 作图像级 mask 清洗备选**

**理由（逐条对证据）**

1. **接口最贴合现有管线**：项目已有 GroundingDINO 猫框（`pet-background-removal/design.md:9`），SAM2 原生接受 box prompt 且实测 J&F 74.4（论文 Table 4 行471-476）→ **零标注接入**。BiRefNet/RVM 虽也能用 box（RVM 不能，BiRefNet 仅可选 box-guided），但 RVM **完全不接受 box**。
2. **输出即二值 mask**，与 spec「猫像素保留、其余置黑」直接对齐（spec `specs/motion-pipeline/spec.md:5`）；SAM2 无 alpha 需要转（论文/代码无 matting 头）。
3. **时序一致性来自 memory attention + memory bank + 遮挡头**（论文 行233-266, 873-877），是**为"背景随相机运动"场景设计的机制性方案**，直接命中 `proposal.md - Why` 的核心痛点（followcam 背景持续变化）。BiRefNet 逐帧无任何时序约束（`BiRefNet_inference_video.ipynb`）→ **必然闪烁**。
4. **零样本对象泛化覆盖动物**（论文 行287-289、行1210 野生动物零样本集），是三者中唯一有动物评测证据的。
5. **许可证干净**（Apache 2.0），无 GPL 传染风险。
6. **吞吐可行**：43 万帧量级，B+ 级约 2h、L 级约 3h GPU 时间（推算），落进 design 的「小时级」目标（`design.md:18`）。

**已知风险与对应缓解**

| 风险 | 证据 | 缓解 |
|---|---|---|
| **猫胡须/细毛 + 快速运动丢分割** | 论文 Limitations 行839 明说 | ①掩码膨胀 2–3px（design D3 已列）；②质量闸门用 IoU 漂移触发**中途补 box prompt 重置传播**（SAM2 支持任意帧补 prompt，行835-839）；③下游是特征级任务，边缘容忍度高（`design.md:167`） |
| 长时遮挡/镜头切换丢目标 | 论文 §C 行835-839 | 遮挡头给出在场分数（行873-877）；按帧标"无猫"而非硬造 mask（spec 兜底场景） |
| 多猫场景需逐 obj 处理，速度下降 | 论文 行835-839（"processes each object separately"） | 多猫取并集（design D3）；或仅在单猫片段做身份训练 |
| 掩码二值化 + resize 到原分辨率有锯齿 | 1024² 内部处理（yaml:89），输出 resize 回原尺寸（`_get_orig_video_res_output`） | 与 spec「下游不要求羽化」一致（design D1） |
| 权重可达性 | 本机 fbaipublicfiles 206 OK，**pet 侧未测** | 备选 HF `facebook/sam2.1-hiera-*`，或回退 BiRefNet（MIT/HF 镜像实测可达） |

**备选定位**

- **RVM —— 仅作"毛发边缘"对照，不建议主用**：三重否决 → ①训练域纯人类（行201/227/262），**论文未说明对猫效果**，有把猫整段抹掉的风险；②GPL-3.0 传染；③依赖 torch 1.9（`requirements_inference.txt`）与项目环境冲突。若三方实测发现猫毛发边缘明显优于 SAM2，可考虑**仅用于边缘 refine**，而非主分割。
- **BiRefNet —— 作图像级 mask 清洗/静帧抠图备选**：类别无关 + hair-level 精度（行745-746）+ MIT + 17 FPS@4090，适合**固定机位静帧**或对 SAM2 输出做**单帧质检**，但**不能作为视频主方案**（逐帧闪烁，官方 notebook 无平滑）。

**下一步（属 `pet-background-removal` tasks 1.1–1.3，未执行）**：按 design D2 在 pet 上跑 3–5 段三方对比，实测项建议补：掩码面积/IOU 抖动统计（帧间闪烁量化）、猫在场率、单段 wall-clock、显存峰值。**本次为只读调研，未运行任何模型，未修改任何文件。**

---