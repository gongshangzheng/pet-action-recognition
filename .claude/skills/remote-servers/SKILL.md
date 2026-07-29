---
name: remote-servers
description: |
  远程训练/推理服务器的使用指南。说明 pet（2× RTX 4090，已搭好 mmaction2 环境）和 A100（≥4× A100-80GB，待启用）的 SSH、conda 环境、端口转发、IP 重 pin、GPU 共享注意事项、开发闭环。
  触发场景：(1) 在远程跑训练/推理/speed run (2) 端口转发看 web (3) ssh 连不上 pet (4) 要用 A100 (5) 远程环境/依赖排坑
---

# 远程服务器使用指南

> **铁律**：训练、测试、推理、speed run、checkpoint 下载等所有 GPU/重算活**都必须在远程服务器（pet / A100）上跑**，不在本地 mac。本地只改代码 + push。详见 [[training]] 和 [[testing]] skill。

## 辅助脚本（`.claude/skills/remote-servers/scripts/`）

| 脚本 | 用途 |
|------|------|
| `reconnect_tunnel.sh` | 重建 autossh 隧道（3000+8788），浏览器连不上时用 |
| `restart_services.sh` | 重启 pet 上的 uvicorn 后端（代码更新后需重启） |
| `full_reconnect.sh` | 全量重连：SSH 检查 → pet_repin（如需）→ 重启 uvicorn → 重建隧道 → 验证 |

## 服务器一览

| 别名 | 硬件 | 角色 | 环境 | 状态 |
|------|------|------|------|------|
| `pet` | 2× RTX 4090 D (24GB) | 训练/推理/speed run | conda env `pet`（py3.10 + torch2.1.2cu121 + mmaction2 1.2.0） | ✅ 就绪 |
| `A100` | ≥4× A100-SXM4-80GB | 重训练（大模型/大数据） | 未搭建 | ⏳ 待启用 |

## 1. pet 服务器

### SSH
```bash
ssh pet          # wyy@pet，已免密（公钥已推）
# HostName pin 在 ~/.ssh/config（remote.mghus.top frp，动态电信宽带 IP）
```

### conda 环境
```bash
~/miniconda3/envs/pet/bin/python          # mmaction2 环境（torch 2.1.2+cu121, mmcv 2.1.0, numpy 1.26.4）
~/miniconda3/envs/pet/bin/pip             # 装包
~/miniconda3/envs/pet/bin/mim             # openmim
# 三大版本坑：numpy 必须 <2（torch 2.1 按 numpy 1.x 编）；mmcv 必须 <2.2.0（mmaction2 1.2.0 硬约束）；opencv 钉 4.10.0.84（5.x 要 numpy≥2）
```

### 起服务 + 端口转发
```bash
# pet 上起后端（uvicorn）+ 前端（vite）
cd ~/pet-action-recognition
~/miniconda3/envs/pet/bin/python -m uvicorn server.main:app --host 127.0.0.1 --port 8788 &
cd web && PATH=~/miniconda3/bin:$PATH npx vite --port 3000 --strict-port --host 127.0.0.1 &

# 本地端口转发（autossh，自动重连）
pkill -f "autossh.*3000"; AUTOSSH_GATETIME=0 autossh -M 0 -L 3000:localhost:3000 -L 8788:localhost:8788 pet -N \
  -o ExitOnForwardFailure=yes -o ServerAliveInterval=20 -o ServerAliveCountMax=3 &

# 本地浏览器开 http://localhost:3000/pet-action-recognition/
# ⚠️ 本地 Clash 代理会拦 localhost → curl 加 --noproxy '*'；浏览器若空白 → Clash 绕过 localhost
```

### IP 变了（ssh 连不上）
```bash
bash scripts/pet_repin.sh    # dig remote.mghus.top → 逐个 nc 探活 → 改 ~/.ssh/config HostName + ssh-keygen -R
```

### GPU 共享（pet 是共享机）
- pet 被多个用户共用（如 `xwy` 跑训练）。跑前先 `nvidia-smi` 看卡空不空。
- 两块卡都可能被占 → speed run 用 `--device cuda:0` 或 `cuda:1`（看哪块空）。
- 大模型（VideoMAE/Swin ~4-11GB）在卡被占时会 OOM → 等卡空再跑全量。

### NAS 外部存储
- `/home/wyy/mnt/` 是 CIFS 挂载（`//192.168.110.4/home`，wyy 的 NAS home share，可写，39TB 空闲）。
- UCF101 数据集在 `/home/wyy/mnt/ucf101/UCF-101/`（101 类，13320 .avi）。
- `datasets/ucf101` 软链到 NAS（`ln -s /home/wyy/mnt/ucf101/UCF-101 datasets/ucf101`）。

### 开发闭环
```
本地改代码 → git push pet main（updateInstead 自动刷新 pet 工作树）→ ssh pet 跑训练/测试/speed run
```

### 产物位置
- checkpoint：`./checkpoints/<model_id>/`（trained + pretrained，gitignore）
- speed run 结果：`results/speedrun/outputs/<model_id>/<video>.mp4` + `results/speedrun/results.json`
- 训练产物：`results/training/`（metrics.json, test_results.json, logs/, work_dirs/）

## 2. A100 服务器（待启用）

```bash
ssh A100        # wyy:33222，主机 `ps`，≥4× A100-SXM4-80GB；密码 `wyunyang`（公钥已推）
# HostName pin 在 ~/.ssh/config（同 frp，端口 33222）
```

### 尚未搭建
- 无 conda env（需 `bash ~/miniconda3.sh` 装）。
- 仓库未 clone（需 `git clone` + `git remote add pet` + push）。
- mmaction2 环境（同 pet 的配方：py3.10 + torch cu121 + mmcv<2.2 + opencv 4.10）。
- 适合大模型（VideoMAE ViT-G / Swin / TimeSformer）的 full-scale 训练（80GB 显存 vs pet 的 24GB）。

### 启用清单
1. 装 conda（同 pet 的 Miniconda3 + TUNA .condarc）。
2. clone 仓库 + push（`git remote add A100 <url>`）。
3. 建 conda env `pet`（同 pet 配方，见 [[using-mmaction2]] §1）。
4. 下 pretrained checkpoints（`scripts/download_checkpoint.py --all`）。
5. 数据集软链（如果 NAS 也挂载了；否则本地拷贝或下到本地磁盘）。

## 3. 两个服务器的 git 关系
```
local (main) ←→ origin (GitHub)
  ↕ push pet main（updateInstead）
  ↕ push A100 main（待启用）
```

## 4. 常见问题
- **ssh 连不上 pet**：IP 可能变了 → `bash scripts/pet_repin.sh`。
- **浏览器 localhost 空白**：本地 Clash 代理拦 localhost → Clash 绕过 `localhost,127.0.0.1,::1`。
- **speed run 视频播不了**：确认标注视频是 H.264（`ffmpeg -i out.mp4 | grep h264`）；cv2 默认写 mp4v → 浏览器不支持（`_infer.py` 的 `_transcode_h264` 已修）。
- **OOM**：GPU 被别的用户占着 → `nvidia-smi` 看哪块空 → `--device cuda:0/1`；等卡空再跑全量。
