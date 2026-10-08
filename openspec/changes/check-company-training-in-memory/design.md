# 设计与只读依据

现有公司环境 `/home/work/analysis_code/.runtime/pet`，一张空闲 A30，GPU 模型顺序执行，CPU 两线程。全部检查设置超时，不进行完整 epoch、验证集评测或独立前向复测。

## 动作识别的数据适配

实际目录是 `dataset-wyy` 与 `annotation-wyy`。视频目录有 2,737 个正常 `.mp4` 与 2,737 个 `._` AppleDouble 元数据文件；后者不能作为视频。`merged_annotations.json` 有 2,737 个 Label Studio task；`merged_annotations.csv` 有 2,626 行，字段包括 `video`、`behavior`。behavior 是 `ranges` 与 `timelinelabels`，包含 12 种已出现的行为，3,927 个范围均为整数且 start≥1、end≥start。

CSV 原路径采用 Label Studio `/data/upload/...`。直接取 basename 没有匹配；移除单个八位十六进制上传前缀后有 1,574 行准确匹配现有文件。只对已有精确文件名关系做内存适配，不改 CSV/JSON，不做模糊匹配或重命名，暂不处理其余未匹配记录。类别名称排序生成仅测试使用的 12 类映射，不声称冻结正式类别词表。

选择两段能对应现有视频且有效的不同类别区间。按 Label Studio 标准以 1 起始帧号转为 0 起始索引，端点包含在窗口中；核对解码帧数，拒绝超界区间。每段仅取区间内最多 32 个连续帧，保留裁剪起止索引；逐帧缩小后保留内存。短区间允许 MMAction2 SampleFrames 重复采样，但不得读取区间外画面。范围基数和端点口径仅供流程检查，正式转换前仍需核对原标注模板。

通过 BaseActionDataset 的内存 records、DataLoader、Compose 和 ArrayDecode 进入 MMAction2，batch=2、workers=0。TSN 保留代表训练增强；X3D-S 将测试配置改为单片段训练采样与中心裁剪，interval=1，并明确它是小规模适配而非原评测配方。两者在内存调整分类头为 12 类，严格保留可匹配的公开 K400 backbone/头部非类别参数，仅跳过类别输出层的形状冲突参数。

调用真实 `model.train_step` 与 MMEngine `OptimWrapper`。优化器在 step 前审计所有梯度，在 step 后对参数采样比较；要求有限非零梯度和真实权重变化，不接受仅 BN 状态变化。检查至少 backbone 与分类头都能收到非零梯度。正式 `scripts/train_model.py` 会写日志、指标和 checkpoint，因此此次不直接执行它；通过底层接口不能冒充已验证正式 CLI、完整 Runner、恢复训练和长时间收敛。

## 其他训练候选

所有辅助输入/标签为明确标记的合成几何监督：YOLO11n 使用官方检测/分割 criterion，batch=2、128px、COCO cat=15；MobileNetV3-Small 在内存替换二分类头，交叉熵；LR-ASPP 使用 VOC 类别里的 cat=8，交叉熵掩码；U2-NetP 从已缓存上游 ZIP 读取单个模型源码到内存，严格加载已有 `.pth`，对七个输出使用 BCE；TCN 使用小型随机初始化网络与序列交叉熵。预训练 YOLO 模型需显式允许梯度，所有测试禁止高层 trainer 的自动保存、自动下载与安装。

U2-NetP 的 PyTorch 训练能力与 rembg 的 ONNX 推理是两个接口。缺少真实猫框、掩码、存在性负样本及动作边界训练集，所以这些辅助测试只能证明可训练，不能证明已建立可用的数据管线或有效模型。非模型/推理后端无需训练，跳过。

## 无写入边界

设置离线环境、禁止网络连接、禁止公司数据根目录写入，以及项目 results/checkpoints/datasets/data/live/weights 的写入；禁止生成媒体、标注、日志、checkpoint 等数据文件。关闭 Python 字节码和 CUDA 持久 JIT 缓存。第三方包的临时代码初始化不包含训练输入或权重。脚本前台执行，stdout 不重定向。
