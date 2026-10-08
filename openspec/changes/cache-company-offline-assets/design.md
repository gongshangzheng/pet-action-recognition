# Design

1. 从 registry AST 提取已注册的公共 checkpoint；按 URL 去重，保持已有
   `checkpoints/<model_id>/<model_id>_pretrained.pth` 和 JSON 元数据约定。
2. 追加轻量候选、初始化 backbone、字体、AMP 自检模型等显式清单；
   GitHub release API 用于发现实际资产名/大小/官方 digest，源码固定为 commit SHA。
3. GroundingDINO 使用公开 Hugging Face 仓库的固定 revision，并准备模型、
   tokenizer、processor 和 config；原始候选源码缓存为 ZIP，不执行未知代码。
4. RKNN 取官方 v2.3.2 可用的文档、Linux runtime/header 和板端 Python wheel；
   板端材料只缓存，不能安装到 x86 服务器或冒充厂商 BSP/驱动。
5. 使用有上限的并发下载、超时、断点续传、保留部分下载及逐项状态。
   不关闭 TLS 校验，不向外部站点发送公司文件或凭据。
6. 已有文件先核验后复用；禁止覆盖内容不一致的已有文件。下载完成后检查
   长度、HTML/LFS 指针误下载、ZIP 完整性及上游提供的 hash，计算 SHA256。
   pickle 权重只检查封装/文件哈希，不做反序列化、模型构建或前向。
7. 原始下载、官方响应、固定 revision 和说明存项目路径。公开源码/文档的
   许可随快照保留，模型是否适合项目由后续实验决定。
8. 路径：权重在 `checkpoints/`，源码/runtime 在 `third-party/offline/`，
   自动缓存入口在 `.runtime/cache/`；报告在 `results/deployment/company_assets_20260930/`。
9. 针对源码额外依赖优先保存 requirements 和兼容 wheel/sdist 供后续处理，
   不为了候选项目自动升级核心环境。未准备好或无公共资产的路径如实标记。

验收是“清单中资产下载与文件完整性”，不等同于离线运行/精度/实机测速验收。

## 2026-10-08 续传核对

首次清单 99 项，其中 86 项已校验（5,658,538,035 字节）。MMAction2 的
25 份去重权重全部存在；部分失败来自网络，也有旧版 ResNet TAR 封装误判。
续传保留原下载，修复 TAR 校验，并在已记录 SHA256 的约束下复用文件。
NanoDet 改用实际含权重的 v1.0.0-alpha-1，Rockchip YOLO11 源码仓库为
airockchip/ultralytics_yolo11。补官方优化 ONNX、U2-Net 可训练权重、候选依赖
wheel/sdist（只缓存），以及 ModelScope 的原生 GroundingDINO+BERT 备用。
ModelScope 文件固定到 revision 并校验其 API 提供的完整 SHA256；原生格式不
冒充 Transformers 格式，HF 路径失败仍在报告保留。rembg 已知 MD5 来自其源码。
Google Drive 返回的网页不得当权重；无法完成的项必须列出，不得宣称全部离线可用。
