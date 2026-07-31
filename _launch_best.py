"""launcher: 验证 --resume auto 全量恢复（optimizer/scheduler/epoch）。

复用 ckpt-verify 的 run_id + work_dir（已有 epoch_6.pth + epoch_6_optim.pth），
--resume auto → train_model.py 重建 combined → mmengine 从 ep6 续训到 ep8。
若 loss 不重置到初始（~1.5）而是延续 ep6 末尾值，说明 optimizer 已恢复。
"""
import sys, os, time
sys.path.insert(0, "/home/wyy/pet-action-recognition")
os.environ["CUDA_VISIBLE_DEVICES"] = "1"

RID = "train-20260731-154458-ckpt-verify"

sys.argv = [
    "train_model.py",
    "--model-id", "videomaev2-base",
    "--dataset-id", "pet_action_mammal_v0",
    "--run-id", RID,
    "--resume", "auto",
    "--mmaction2-config", "configs/pet_mammal_videomaev2_base_16x4.py",
    "--epochs", "8",
    "--lr", "0.0001",
    "--batch-size", "2",
    "--device", "cuda",
    "--num-classes", "7",
    "--vis-interval", "99",
]

print("[launcher] resume", RID, flush=True)
from scripts.train_model import main
sys.exit(main())
