"""launcher: 验证 checkpoint 拆分（weights/optim/json）+ max_keep=1 + resume 重建。

VideoMAEv2，6ep（interval=5 → 在 ep5+ep6 各存一次，验证 max_keep=1 裁剪到 ep6）。
无高级超参 → cfg_path 直接用 user config（含 OptimizerCheckpointHook），
测 meta_fields 注入 + epoch_N.json sidecar。
"""
import sys, time, os
sys.path.insert(0, "/home/wyy/pet-action-recognition")

# GPU0/1 被其他用户占用，用 GPU1（剩 ~7.7GB）+ bs=2
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

run_id = f"train-{time.strftime('%Y%m%d-%H%M%S')}-ckpt-verify"

sys.argv = [
    "train_model.py",
    "--model-id", "videomaev2-base",
    "--dataset-id", "pet_action_mammal_v0",
    "--run-id", run_id,
    "--name", "checkpoint-split verify (6ep, GPU1, bs2)",
    "--description", "验证 weights/optim/json 拆分 + max_keep=1 + meta_fields sidecar",
    "--mmaction2-config", "configs/pet_mammal_videomaev2_base_16x4.py",
    "--epochs", "6",
    "--lr", "0.0001",
    "--batch-size", "2",
    "--device", "cuda",
    "--num-classes", "7",
    "--vis-interval", "99",
]

print("[launcher] run_id =", run_id, flush=True)
from scripts.train_model import main
sys.exit(main())
