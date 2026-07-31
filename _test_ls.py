"""验证 label_smoothing 修复：override config 里 import + LabelSmoothLoss 注册 + 构建 + forward。"""
import sys, types, os, torch
sys.path.insert(0, "/home/wyy/pet-action-recognition")
from scripts.train_model import _maybe_write_override
from mmengine.config import Config
from mmaction.registry import MODELS

REPO = "/home/wyy/pet-action-recognition"
user_cfg = os.path.join(REPO, "configs/pet_mammal_videomaev2_base_16x4.py")

args = types.SimpleNamespace(
    run_id="test-ls-dryrun",
    weight_decay=0.05,
    backbone_lr_mult=0.2,
    label_smoothing=0.1,
    num_clips_val=None,
    override_snippet="",
)
override = _maybe_write_override(args, user_cfg, n_cls=7)
print("=== override content ===")
print(open(override).read())

print("=== mmengine 加载（import 是否生效）===")
cfg = Config.fromfile(override)
print("loss_cls:", cfg.model.cls_head.loss_cls)

print("=== 构建 loss + forward ===")
loss = MODELS.build(cfg.model.cls_head.loss_cls)
print("built loss:", type(loss).__name__, "eps=", loss.epsilon)
logits = torch.randn(4, 7)          # batch=4, 7 classes
labels = torch.tensor([0, 1, 2, 3])
out = loss(logits, labels, avg_factor=4.0)   # 模拟 head 调用（带 avg_factor）
print("forward ok, loss=", float(out))
