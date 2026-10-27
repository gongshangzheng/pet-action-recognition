# 测试设计

使用 `/home/work/analysis_code/.runtime/pet`，RKNN-Toolkit2 2.3.2；远程 CPU 两线程，单进程前台执行，设置 240 秒整体超时。

网络为随机初始化 Conv2d(3→4,3×3) → ReLU → GlobalAveragePool → Flatten，静态输入 `[1,3,32,32]`，输出 `[1,4]`。固定种子产生两组输入：随机值和零值；第二组验证模拟器确实接受新输入。PyTorch 导出 ONNX 至 BytesIO，并用 ONNX checker 和 ORT CPU 验证同一图。

`rknn.config(target_platform='rv1126b', float_dtype='float16')` 指定编译目标；`load_onnx` → `build(do_quantization=False)` → `init_runtime(target=None)` 使用软件模拟器。若非量化路径不支持，不静默更换平台或编造成功。本次不补 INT8 校准，不调用 eval_perf，不连接实体板。

参考 FP32 PyTorch 对 ORT 采用 atol=1e-5、rtol=1e-4；RKNN FP16 对同一参考采用 atol=0.002、rtol=0.02，报告最大/平均绝对偏差、形状和有限性。这是小网络功能验证容差，不是猫检测精度指标。检查两个输入得到不同输出。

## 临时文件与无保存约束

SDK API 接收 ONNX 路径，编译器会创建临时模型/中间文件。服务器 `/dev/shm` 已确认是有余量的 tmpfs。分配专属内存目录，并从项目 `.runtime/rknn-ram-<uuid>` 建临时链接；CWD、TMPDIR、TMP/TEMP、Matplotlib/XDG 缓存均指向该内存空间。所有模型编译文件仅放这里，不保留报告、预测、输入数组或 SDK 日志。Python 字节码关闭；不调用 export_rknn/accuracy_analysis。

Python audit 阻止网络连接和内存空间之外的写入（stdout/stderr 除外）。读取既有环境允许，但绝不改核心依赖、原权重或公司数据。释放 RKNN 后恢复 CWD，删除项目临时链接，关闭内存目录并清除；超时/异常走同一清理路径。可复用脚本只放项目 scripts，不在临时目录生成自有脚本。原生编译器依赖自身运行时，CWD 与临时变量使其输出也进入上述内存目录。

## 覆盖与失败处理

通过仅证明一个 Conv/ReLU/Pool 网络的 RV1126B 软件模拟路径可用。YOLO、MobileNet、U2-NetP、TCN 与动作模型的完整转换/量化仍需逐项验证。若当前系统/SDK 本地库缺少依赖，先只读定位并优先尝试既有库路径；不升级已工作的 PyTorch/MMCV 环境。
