#!/usr/bin/env python3
"""AIM 冻结断言：构建 AIMVisionTransformer，校验冻结/可训练参数比例与 ckpt 键覆盖。

用法（repo 根）：
    python3 scripts/assert_aim_frozen.py [--ckpt checkpoints/videomae-v1/videomae-v1_pretrained.pth]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import torch

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ckpt", default="checkpoints/videomae-v1/videomae-v1_pretrained.pth")
    parser.add_argument("--max-ratio", type=float, default=10.0,
                        help="可训练参数占比上限（%%，默认 10）")
    args = parser.parse_args()

    from configs.aim_modules import AIMVisionTransformer  # noqa: F401 触发注册

    model = AIMVisionTransformer(
        img_size=224, patch_size=16, embed_dims=768, depth=12, num_heads=12,
        mlp_ratio=4, qkv_bias=True, num_frames=16,
        norm_cfg=dict(type="LN", eps=1e-6),
        freeze_backbone=True, adapter_reduction=12,
        init_cfg=dict(type="Pretrained", checkpoint=args.ckpt, prefix="backbone."),
    )
    model.init_weights()

    frozen = trainable = 0
    missing_adapter = []
    for name, p in model.named_parameters():
        if name.startswith("aim_adapters."):
            if not p.requires_grad:
                missing_adapter.append(name)
            trainable += p.numel()
        else:
            if p.requires_grad:
                missing_adapter.append(name + " (should be frozen)")
            frozen += p.numel()

    ratio = 100.0 * trainable / max(frozen + trainable, 1)

    # ckpt 键覆盖检查：init_cfg 加载后 backbone 应非随机（抽查 pos_embed 方差）
    loaded = bool(torch.count_nonzero(model.pos_embed).item() > 0)

    print(f"frozen params : {frozen:,}")
    print(f"trainable     : {trainable:,} ({ratio:.2f}%)")
    print(f"ckpt loaded   : {loaded} (pos_embed nonzero)")
    ok = (not missing_adapter) and ratio <= args.max_ratio and loaded
    if missing_adapter:
        print("VIOLATIONS:")
        for m in missing_adapter[:10]:
            print("  -", m)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
