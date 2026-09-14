# Tasks: provision-a100-server

## 0. 违规披露处置（用户决定）

- [ ] 0.1 用户选择已提前动作（miniconda 安装 / repo clone）的处置：a) 勾选视为完成；b) 清除后从 1.1 从零执行

## 1. A100 基础环境

- [ ] 1.1 conda 配置：.condarc 用 TUNA 镜像（pip 走 TUNA 或阿里镜像）
- [ ] 1.2 仓库就位：~/pet-action-recognition（clone 自 bundle），`git remote add A100` 配置到本地仓库
- [ ] 1.3 数据传输：scp 1 段白天 cats 视频（event_20260806_120311.mp4）至 A100:~/data/cats/

## 2. plf 环境

- [ ] 2.1 conda create -n plf python=3.10；pip 安装 torch/torchvision（cu121）、transformers、accelerate、supervision、opencv-python-headless
- [ ] 2.2 环境验证：torch.cuda 可用 ×4 卡、transformers 版本 ≥4.46（GroundingDINO 原生支持）

## 3. Spike Demo（用户验收点）

- [ ] 3.1 权重下载：GroundingDINO（HF：IDEA-Research/grounding-dino-tiny，经 hf-mirror）；HQ-SAM 权重可得性探测（不可得则 demo 降级为纯检测，如实说明）
- [ ] 3.2 单段视频 spike：检测 → 简单 IoU 跟踪 → 猫居中稳定裁剪（768×768）
- [ ] 3.3 产出：跟随视角视频 + 原图/跟随对比视频 + 检测框接触表（JPG），回传本地供用户查看
- [ ] 3.4 **用户验收**：通过 → pet-motion-latent-pipeline 的 0A.2 勾选；不通过 → 方案重评

## 4. 收尾

- [ ] 4.1 A100 连接方式写入 remote-servers skill（状态从"待启用"更新为"管线专用"）
- [ ] 4.2 提交 change 与 skill 更新（docs/chore: 前缀）
