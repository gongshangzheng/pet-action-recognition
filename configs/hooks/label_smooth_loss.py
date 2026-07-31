"""Label smoothing loss — 封装 torch.nn.CrossEntropyLoss(label_smoothing)。

为什么存在：本环境 mmaction 自带的 CrossEntropyLoss 不支持 label_smoothing 参数，
也没有 LabelSmoothLoss 类（LabelSmoothLoss 未注册）。本 wrapper 注册为
``'LabelSmoothLoss'``，供 override config 用：

    model = dict(cls_head=dict(loss_cls=dict(type='LabelSmoothLoss', epsilon=0.1)))

用法：softmax 多分类（pet 任务）。use_sigmoid 仅做 API 兼容，实际走 softmax CE。
"""
import torch.nn as nn
from mmengine.registry import MODELS


@MODELS.register_module(force=True)
class LabelSmoothLoss(nn.Module):
    """Cross-entropy + label smoothing，签名兼容 mmaction head 调用约定。"""

    def __init__(
        self,
        epsilon: float = 0.1,
        num_classes: int = -1,
        loss_weight: float = 1.0,
        use_sigmoid: bool = False,
        reduction: str = "mean",
        class_weight=None,
        **kwargs,
    ):
        super().__init__()
        self.loss_weight = loss_weight
        self.epsilon = epsilon
        weight = class_weight if class_weight is not None else None
        self.criterion = nn.CrossEntropyLoss(
            label_smoothing=epsilon,
            reduction=reduction,
            weight=weight,
        )

    def forward(self, cls_score, label, **kwargs):
        # mmaction head 可能传 avg_factor / weight_avg_factor 等额外 kwargs；
        # nn.CrossEntropyLoss(reduction='mean') 已按 batch 均值，等价于 avg_factor 归一。
        return self.loss_weight * self.criterion(cls_score, label)
