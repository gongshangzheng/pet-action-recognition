"""实测 mmengine DictAction 能否把 --cfg-options 的 {...} 字典值解析成 dict。"""
import argparse
from mmengine.config import Config, DictAction

cfg = Config.fromfile("configs/pet_mammal_videomaev2_base_16x4.py")

# 模拟命令行：python tool.py config --cfg-options key=value key2=value2 ...
argv = [
    "--cfg-options",
    "optim_wrapper.optimizer.weight_decay=0.1",
    "optim_wrapper.paramwise_cfg={'custom_keys':{'backbone':{'lr_mult':0.1}}}",
    "model.cls_head.loss_cls={'type':'LabelSmoothLoss','epsilon':0.1,'num_classes':7}",
    "val_dataloader.dataset.pipeline.1.num_clips=5",
]

parser = argparse.ArgumentParser()
parser.add_argument("--cfg-options", nargs="+", action=DictAction, default={})
args = parser.parse_args(argv)

print("parsed cfg_options:", args.cfg_options)
cfg.merge_from_dict(args.cfg_options)

print("weight_decay:", repr(cfg.optim_wrapper.optimizer.weight_decay))
print("paramwise_cfg:", repr(cfg.optim_wrapper.paramwise_cfg), type(cfg.optim_wrapper.paramwise_cfg))
print("loss_cls:", repr(cfg.model.cls_head.loss_cls), type(cfg.model.cls_head.loss_cls))
print("val num_clips:", repr(cfg.val_dataloader.dataset.pipeline[1].num_clips))
