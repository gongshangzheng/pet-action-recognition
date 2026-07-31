"""OptimizerCheckpointHook — 伴生 CheckpointHook，把 optimizer/scheduler/message_hub
单独存到 ``epoch_N_optim.pth``，并写一份训练元信息 JSON sidecar。

为什么：主 ``CheckpointHook`` 在本项目的 config 里被设成
``save_optimizer=False, save_param_scheduler=False``（→ ``epoch_N.pth`` 只含 weights，
小而干净，便于评测/推理/load_from）。但 resume 需要 optimizer/scheduler/message_hub，
故由本 hook 另存一份 ``epoch_N_optim.pth``。resume 时 train_model.py 会把 weights + optim
合并成一个临时完整 .pth 交给 mmengine（见 ``_reconstruct_resume_ckpt``）。

产物（work_dir，每个 checkpoint interval 命中 / 最后一 epoch）：
- ``epoch_N_optim.pth``：``{meta, optimizer, param_scheduler, message_hub}``
- ``epoch_N.json``：训练元信息 sidecar（超参/数据集/版本等，不进 .pth）

prune：与主 hook 同步，按 ``max_keep_ckpts`` 只留最新若干。
"""
from __future__ import annotations

import json
import os
import time

import torch
from mmengine.hooks import Hook
from mmengine.registry import HOOKS
from mmengine.runner import save_checkpoint


def _to_cpu(obj):
    """递归把 dict/list/tuple 里的 tensor 搬到 CPU（镜像 mmengine save_checkpoint 的 apply_to）。"""
    if torch.is_tensor(obj):
        return obj.cpu()
    if isinstance(obj, dict):
        return {k: _to_cpu(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_cpu(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(_to_cpu(v) for v in obj)
    return obj


def _env_versions() -> dict:
    """收集 mmaction2/mmengine/torch/cuda 版本，写进 sidecar 便于复现。"""
    env = {}
    try:
        import torch as _t
        env["torch"] = _t.__version__
        env["cuda"] = _t.version.cuda or ""
    except Exception:
        pass
    try:
        import mmengine
        env["mmengine"] = mmengine.__version__
    except Exception:
        pass
    try:
        import mmaction
        env["mmaction2"] = mmaction.__version__
    except Exception:
        pass
    return env


@HOOKS.register_module()
class OptimizerCheckpointHook(Hook):
    """与 CheckpointHook 同 interval，单独保存 optimizer 状态 + JSON sidecar。

    Args:
        interval (int): 每 N epoch 存一次（应与主 CheckpointHook.interval 一致）。
        max_keep_ckpts (int): optim/json 文件保留个数，超出删最旧；0 = 不限。
        meta_fields (dict): 写进 epoch_N.json 的训练元信息（run_id/model_id/超参…），
            由 train_model.py 经 --cfg-options 注入。
    """

    priority = "LOWEST"  # 在 CheckpointHook 之后跑，保证该 epoch 的 weights 已存

    def __init__(self, interval: int = 1, max_keep_ckpts: int = 1, meta_fields: dict | None = None):
        self.interval = interval
        self.max_keep_ckpts = max_keep_ckpts
        self.meta_fields = dict(meta_fields or {})

    def _should_save(self, runner, epoch: int) -> bool:
        if epoch % self.interval == 0:
            return True
        # 最后一 epoch 也要存（与主 hook 的 save_last 对齐）
        max_ep = getattr(runner, "max_epochs", None)
        return max_ep is not None and epoch >= max_ep

    def _prune(self, work_dir: str) -> None:
        """无状态裁剪：扫 work_dir 的 epoch_*_optim.pth，只留最新 max_keep 个（含同名 .json）。

        用扫描而非内存计数：resume 时本 hook 是新实例，内存计数会丢、旧 _optim 残留。
        主 CheckpointHook 靠 message_hub 持久化 keep_ckpt_ids，本 hook 无此机制故扫盘。
        """
        if self.max_keep_ckpts <= 0:
            return
        import glob
        import re
        optims = glob.glob(os.path.join(work_dir, "epoch_*_optim.pth"))

        def _ep(p: str) -> int:
            m = re.search(r"epoch_(\d+)_optim\.pth$", os.path.basename(p))
            return int(m.group(1)) if m else 0

        optims.sort(key=_ep, reverse=True)  # newest first
        for p in optims[self.max_keep_ckpts:]:
            try:
                os.remove(p)
            except OSError:
                pass
            jp = p[: -len("_optim.pth")] + ".json"  # epoch_N_optim.pth → epoch_N.json
            if os.path.isfile(jp):
                try:
                    os.remove(jp)
                except OSError:
                    pass

    def after_train_epoch(self, runner) -> None:
        epoch = runner.epoch + 1
        if not self._should_save(runner, epoch):
            return

        work_dir = runner.work_dir
        meta = dict(epoch=epoch, iter=runner.iter)

        # --- optim 文件：{meta, optimizer, param_scheduler, message_hub} ---
        ckpt = {
            "meta": meta,
            "optimizer": _to_cpu(runner.optim_wrapper.state_dict()),
            "param_scheduler": [_to_cpu(s.state_dict()) for s in runner.param_schedulers],
            "message_hub": _to_cpu(runner.message_hub.state_dict()),
        }
        optim_path = os.path.join(work_dir, f"epoch_{epoch}_optim.pth")
        save_checkpoint(ckpt, optim_path)
        runner.logger.info(f"[OptimizerCheckpointHook] saved optim → epoch_{epoch}_optim.pth")

        # --- JSON sidecar ---
        sidecar = {
            **self.meta_fields,
            "saved_epoch": epoch,
            "saved_iter": runner.iter,
            "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "env": _env_versions(),
        }
        json_path = os.path.join(work_dir, f"epoch_{epoch}.json")
        tmp = json_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(sidecar, f, ensure_ascii=False, indent=2)
        os.replace(tmp, json_path)

        # --- 无状态裁剪（resume 安全）---
        self._prune(work_dir)
