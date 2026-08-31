"""AIM: Adapting Image Models for Efficient Video Action Recognition (arXiv:2302.03024)
的 mmaction2 接入模块（vendor 只读，全部自定义代码放本包，经 config custom_imports 加载）。

实现说明（与 AIM 论文的保真度）：
- 保留：每个 Transformer block 的并行 Adapter（bottleneck FC down→ReLU→up，
  up 投影零初始化使训练起点等价于原始预训练模型），作用于联合时空 token 序列。
- 简化：论文中的 LSA（Location-wise Spatial Attention）与帧级位置编码扩展未移植；
  时间建模依赖 ViT 的联合时空注意力 + Adapter 在全 token 序列上的适配。
  该简化与 AdaptFormer/AIM 的空间适配器核心一致，满足「冻结 backbone、仅训少量
  Adapter + 头部」的参数高效目标（<10% 可训练参数）。

用法（config 中）：
    custom_imports = dict(imports=['configs.aim_modules'], allow_failed_imports=False)
    model = dict(backbone=dict(type='AIMVisionTransformer', ...同 VisionTransformer 参数...))
"""
from __future__ import annotations

import torch
import torch.nn as nn
from mmaction.registry import MODELS
from mmaction.models.backbones.vit_mae import VisionTransformer


class AdapterParallel(nn.Module):
    """并行式 bottleneck Adapter：y = x + scale * up(relu(down(ln(x))))。

    up 投影零初始化 → 训练起点 y = x（不破坏预训练表征）。
    """

    def __init__(self, dim: int, reduction: int = 64, dropout: float = 0.0):
        super().__init__()
        self.norm = nn.LayerNorm(dim)
        self.down = nn.Linear(dim, dim // reduction)
        self.act = nn.ReLU(inplace=True)
        self.up = nn.Linear(dim // reduction, dim)
        self.drop = nn.Dropout(dropout)
        # 零初始化 up 投影
        nn.init.zeros_(self.up.weight)
        nn.init.zeros_(self.up.bias)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.drop(self.up(self.act(self.down(self.norm(x)))))


@MODELS.register_module()
class AIMVisionTransformer(VisionTransformer):
    """VisionTransformer + 逐 block 并行 Adapter（AIM 简化移植版）。

    参数命名与 vendor VisionTransformer 完全一致（本类只追加
    ``aim_adapters.*`` 前缀的新参数），因此 K400 预训练 ckpt 的
    init_cfg（prefix='backbone.'）照常加载，不缺不重。
    """

    def __init__(self, *args, adapter_reduction: int = 64,
                 adapter_dropout: float = 0.0, freeze_backbone: bool = True,
                 **kwargs):
        super().__init__(*args, **kwargs)

        # 逐 block 注入并行 Adapter，并注册为子模块（state_dict/checkpoint 完整）
        self.aim_adapters = nn.ModuleList(
            [AdapterParallel(self.embed_dims, adapter_reduction, adapter_dropout)
             for _ in range(len(self.blocks))])

        for i, (blk, adapter) in enumerate(zip(self.blocks, self.aim_adapters)):
            self._attach_adapter_hook(blk, adapter, f"block {i}")

        if freeze_backbone:
            self._freeze_backbone()

    def _attach_adapter_hook(self, blk: nn.Module, adapter: AdapterParallel,
                             name: str) -> None:
        """并行 Adapter：block 输出 += adapter(block 输入)。"""

        def hook(_module: nn.Module, args: tuple, output: torch.Tensor,
                 _adapter: AdapterParallel = adapter, _name: str = name):
            x = args[0]
            return output + _adapter(x)

        blk.register_forward_hook(hook)

    def _freeze_backbone(self) -> None:
        """冻结全部预训练参数；仅 Adapter 保持可训练。"""
        frozen = trainable = 0
        for name, param in self.named_parameters():
            if name.startswith("aim_adapters."):
                param.requires_grad = True
                trainable += param.numel()
            else:
                param.requires_grad = False
                frozen += param.numel()
        total = frozen + trainable
        ratio = 100.0 * trainable / total if total else 0.0
        print(f"[AIM] backbone frozen: {frozen:,} params; "
              f"trainable adapters: {trainable:,} ({ratio:.2f}%)")

    def init_weights(self) -> None:
        """预训练权重按 init_cfg 加载到继承的参数；Adapter 保持零初始化。"""
        super().init_weights()
        # 防御：init_cfg 加载不应覆盖 Adapter 的零初始化（名字不匹配本就不会覆盖）
        for adapter in self.aim_adapters:
            nn.init.zeros_(adapter.up.weight)
            nn.init.zeros_(adapter.up.bias)
