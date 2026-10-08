# 设计

沿用 `/home/work/analysis_code/.runtime/pet`。运行前查看 GPU，占用一张空闲 A30，batch=1，CPU 线程限制为 2，各模型顺序执行。运行脚本提供超时与逐项错误汇总；所有结果仅在标准输出中。

固定随机种子生成 96 帧 256×256 RGB 图形与纹理。MMAction2 使用现有 `init_recognizer`、`inference_recognizer`，将 Decord 初始化/解码替换成内存 `ArrayDecode`，将多视角评估缩为一个片段/中心裁剪，其余预处理保持对应配置。完整权重仍采用公开的 Kinetics-400 分类头，不当作 AnimalKingdom 微调结果。注册表 `x3d-xs` 实际引用 X3D-S 配置，因此终端明确标注 X3D-S。

YOLO 使用绝对本地 `.pt`、`save=False`、`save_txt=False`，类别映射确认 COCO 猫 ID=15；合成输入空框是合法结果。torchvision 模型构造时禁用默认权重，随后严格加载本地权重。LR-ASPP 权重用于 VOC 21 类分割接口检查，不宣称可直接高质量移除猫背景。

U2-NetP 使用 rembg 的 Session/预测/去背景 API，自定义本地 Session 仅替换下载路径，ONNX Runtime 限制为 CPU 后端和两线程。关闭 Numba JIT 缓存，避免该检查产生缓存数据。TCN 是小型随机初始化因果网络，检查形状及未来扰动不影响之前输出；不当作已训练动作边界模型。PELT 用已知三段特征验证变化点。

组合检查将实际 U2-NetP 掩码应用到合成帧，交给预训练 MobileNetV3-Small，再把分类输出作为接口测试特征送入同一因果 TCN。它是测试适配链路，不修改或冒充正式业务流水线，既不要求检出猫，也不采用伪造框绕过门控。

环境禁自动下载/安装，禁止网络连接；禁 Python 字节码和 CUDA 持久 JIT 缓存。输入与输出只留内存。第三方包初始化所需的临时代码由其自身管理，测试脚本不生成任何数据或结果文件。执行不重定向日志。
