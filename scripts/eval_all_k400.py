"""批量 K400 评测：对所有 K400-pretrained 模型在 K400 val 上跑 formal test。

每个模型 run_test.py → top1/top5/mean1 + 速度/大小，写 test_results.json，
汇总到 results/training/k400_eval_summary.json。

用法（pet 上后台）：
  nohup ~/miniconda3/envs/pet/bin/python scripts/eval_all_k400.py > /tmp/k400_eval.log 2>&1 &
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.routers.training import _MMACTION2_REGISTRY  # noqa: E402
from server.config import resolve_mmaction2_config, CHECKPOINTS_DIR  # noqa: E402

PYTHON = os.path.expanduser("~/miniconda3/envs/pet/bin/python")
GPU = "0"
# 优先用预筛后的 list（decord 预筛剔除坏视频，避免 test loop 崩）；不存在则回退原 list
_ANN_FILTERED = os.path.expanduser("~/mnt/kinetics400/kinetics400_val_list_filtered.txt")
ANN = _ANN_FILTERED if os.path.isfile(_ANN_FILTERED) else os.path.expanduser("~/mnt/kinetics400/kinetics400_val_list_videos.txt")
DATA_ROOT = os.path.expanduser("~/mnt/kinetics400/videos_val")
SUMMARY_JSON = REPO / "results" / "training" / "k400_eval_summary.json"

# 重模型（3D/ViT，多帧）降 batch 避免 OOM；轻模型 batch 4 提速
HEAVY_MODELS = {"i3d-resnet50", "csn-ircsn152", "swin-tiny", "slowfast-resnet50",
                "r2plus1d-resnet34", "tpn-slowonly-r50", "tanet-resnet50",
                "timesformer-divst", "mvit-small", "videomae-base", "videomaev2-base"}
BATCH_FOR = lambda mid: 1 if mid in HEAVY_MODELS else 4
TIMEOUT = 14400  # 单模型最长 4h（重模型 batch1 慢，给够时间）


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def k400_models() -> list[dict]:
    out = []
    for m in _MMACTION2_REGISTRY:
        src = m.get("pretrained_source", "")
        if "Kinetics-400" not in src:
            continue
        if not m.get("mmaction2_config"):
            continue
        out.append(m)
    return out


def read_test_result(run_id: str) -> dict | None:
    mp = REPO / "results" / "training" / "test_results.json"
    if not mp.is_file():
        return None
    try:
        d = json.load(open(mp))
        r = next((x for x in d.get("results", []) if x.get("id") == run_id), None)
        return r
    except Exception:
        return None


def save_summary(summary: list[dict]) -> None:
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(SUMMARY_JSON) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SUMMARY_JSON)


def main() -> int:
    global TIMEOUT
    # --only a,b,c 只跑指定模型（补跑失败项）；--timeout N 覆盖超时
    only = None
    timeout_override = TIMEOUT
    it = iter(sys.argv[1:])
    for a in it:
        if a.startswith("--only="):
            only = set(a.split("=", 1)[1].split(","))
        elif a.startswith("--timeout="):
            timeout_override = int(a.split("=", 1)[1])
    TIMEOUT = timeout_override
    models = k400_models()
    if only:
        models = [m for m in models if m["id"] in only]
    log(f"K400 评测：{len(models)} 个模型，GPU{GPU}，ann={ANN}，timeout={TIMEOUT}s")
    summary: list[dict] = []
    for i, m in enumerate(models):
        mid = m["id"]
        cfg = resolve_mmaction2_config(m["mmaction2_config"])
        ckpt = os.path.join(CHECKPOINTS_DIR, mid, f"{mid}_pretrained.pth")
        if not os.path.isfile(ckpt):
            log(f"[{i+1}/{len(models)}] {mid}: 无 checkpoint {ckpt}，跳过")
            continue
        run_id = f"k400-eval-{mid}-{int(time.time())}"
        args = [
            PYTHON, str(REPO / "scripts" / "run_test.py"),
            "--run-id", run_id,
            "--mmaction2-config", cfg,
            "--checkpoint", ckpt,
            "--dataset-id", "kinetics400",
            "--split", "val",
            "--num-classes", "400",
            "--ann-file", ANN,
            "--data-root", DATA_ROOT,
            "--test-batch-size", str(BATCH_FOR(mid)),
            "--device", "cuda",
        ]
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = GPU
        env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
        log(f"[{i+1}/{len(models)}] {mid}: cfg={os.path.basename(cfg)} batch={BATCH_FOR(mid)}")
        t0 = time.time()
        try:
            proc = subprocess.run(args, env=env, cwd=str(REPO), capture_output=True, text=True, timeout=TIMEOUT)
            rc = proc.returncode
            err_tail = (proc.stderr or proc.stdout or "")[-300:]
        except subprocess.TimeoutExpired:
            rc = -1
            err_tail = "TIMEOUT"
        dt = time.time() - t0
        r = read_test_result(run_id) or {}
        mt = r.get("metrics", {}) or {}
        entry = {
            "model": mid, "run_id": run_id, "exit": rc,
            "top1": mt.get("top1_acc"), "top5": mt.get("top5_acc"),
            "mean1": mt.get("mean1_acc"), "speed": mt.get("speed"),
            "duration_sec": round(dt),
            "error_tail": err_tail.strip() if rc != 0 else "",
        }
        summary.append(entry)
        save_summary(summary)
        log(f"  {mid}: exit={rc} top1={entry['top1']} top5={entry['top5']} mean1={entry['mean1']} {dt:.0f}s")
    done = [s for s in summary if s["top1"] is not None]
    done.sort(key=lambda s: s["top1"], reverse=True)
    log("=== K400 排行 ===")
    for s in done:
        sp = s.get("speed") or {}
        log(f"  {s['top1']:.4f}  {s['model']:22s} mean1={s.get('mean1')} fps={sp.get('fps')} params={sp.get('param_count_m')}M")
    failed = [s["model"] for s in summary if s["exit"] != 0]
    log(f"失败: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
