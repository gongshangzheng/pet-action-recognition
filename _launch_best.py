"""launcher: 用 best-effect 配置跑 VideoMAEv2（走 train_model.main，避开 shell 引号）。"""
import sys, time
sys.path.insert(0, "/home/wyy/pet-action-recognition")

run_id = f"train-{time.strftime('%Y%m%d-%H%M%S')}-vmaev2-best3"
snippet = (
    "param_scheduler = ["
    "dict(type='LinearLR', start_factor=0.1, by_epoch=True, begin=0, end=3), "
    "dict(type='CosineAnnealingLR', T_max=12, eta_min=1e-6, by_epoch=True, begin=3, end=15)"
    "]"
)

sys.argv = [
    "train_model.py",
    "--model-id", "videomaev2-base",
    "--dataset-id", "pet_action_mammal_v0",
    "--run-id", run_id,
    "--name", "VideoMAEv2 best3 (ls+wd+blr+5clip)",
    "--description", "15ep; lr1e-4; wd0.05; label_smooth0.1; backbone_lr_mult0.2; num_clips_val5; 3warmup+12cosine",
    "--mmaction2-config", "configs/pet_mammal_videomaev2_base_16x4.py",
    "--epochs", "15",
    "--lr", "0.0001",
    "--batch-size", "4",
    "--device", "cuda",
    "--num-classes", "7",
    "--vis-interval", "3",
    "--weight-decay", "0.05",
    "--label-smoothing", "0.1",
    "--backbone-lr-mult", "0.2",
    "--num-clips-val", "5",
    "--override-snippet", snippet,
]

print("[launcher] run_id =", run_id, flush=True)
from scripts.train_model import main
sys.exit(main())
