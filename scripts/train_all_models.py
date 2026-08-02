"""批量训练所有识别模型（对比 best_metric）。

GPU0 串行跑 20 个识别模型，每模型用各自 config + pretrained 在 pet_action_mammal_v0 上
finetune 15 epoch。失败（OOM/配置不兼容）跳过，汇总到 results/training/train_all_summary.json。

用法（pet 上后台）：
  nohup ~/miniconda3/envs/pet/bin/python scripts/train_all_models.py > /tmp/train_all.log 2>&1 &
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
DATASET = "pet_action_mammal_v0"
EPOCHS = 15
BATCH = 2
GPU = "0"
SUMMARY_JSON = REPO / "results" / "training" / "train_all_summary.json"

# videomae 系列内置 config 是 eval-only → 用 pet 专用 config（init_cfg 加载 backbone）
PET_CONFIGS = {
    "videomae-base": "configs/pet_mammal_videomae_base_16x4.py",
    "videomaev2-base": "configs/pet_mammal_videomaev2_base_16x4.py",
}
# ViT/Transformer 系用小 lr（AdamW）；CNN 系用 1e-3（SGD finetune）
VIT_MODELS = {"videomae-base", "videomaev2-base", "timesformer-divst", "swin-tiny", "mvit-small"}
# 已知重模型降 bs 避免 OOM
HEAVY_MODELS = {"timesformer-divst", "swin-tiny", "i3d-resnet50", "slowfast-resnet50", "c3d-sports1m", "csn-ircsn152", "r2plus1d-resnet34"}


def log(msg: str) -> None:
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def lr_for(mid: str) -> float:
    return 1e-4 if mid in VIT_MODELS else 1e-3


def real_models() -> list[dict]:
    out = []
    for m in _MMACTION2_REGISTRY:
        if m.get("type", "classification") != "classification":
            continue
        if not m.get("mmaction2_config"):
            continue
        if not m.get("pretrained_url") and m["id"] not in PET_CONFIGS:
            continue  # 跳过 dataset/default 占位
        if m["id"] in ("tsn-resnet50-quadruped",):
            continue  # 合成数据 config，不是 pet_mammal
        out.append(m)
    return out


def resolve_cfg(mid: str, builtin: str) -> str:
    cfg = PET_CONFIGS.get(mid) or builtin
    return cfg if os.path.isabs(cfg) else resolve_mmaction2_config(cfg)


def read_run_metrics(run_id: str) -> dict:
    """从 metrics.json 读 best_metric + speed（train_model.py 训练后记录）。"""
    mp = REPO / "results" / "training" / "metrics.json"
    if not mp.is_file():
        return {}
    try:
        d = json.load(open(mp))
        r = next((x for x in d.get("runs", []) if x.get("id") == run_id), None)
        if not r:
            return {}
        m = r.get("metrics", {}) or {}
        return {"best_metric": r.get("best_metric"), "speed": m.get("speed")}
    except Exception:
        return {}


def find_trainall_run(mid: str) -> str | None:
    """找该 model 最新的 trainall-<mid>-* run_id。"""
    mp = REPO / "results" / "training" / "metrics.json"
    if not mp.is_file():
        return None
    try:
        d = json.load(open(mp))
        ids = [r["id"] for r in d.get("runs", []) if r.get("id", "").startswith(f"trainall-{mid}-")]
        return ids[-1] if ids else None
    except Exception:
        return None


def save_summary(summary: list[dict]) -> None:
    SUMMARY_JSON.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(SUMMARY_JSON) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SUMMARY_JSON)


def benchmark_only() -> int:
    """对已训练的 trainall-* checkpoint 补测速度 + 大小（不重训）。

    结果写到 train_all_benchmark.json + 回填 metrics.json 的 run.metrics.speed
    （前端 TrainResults 的 模型大小/速度 列才能显示）。
    """
    from scripts.benchmark_speed import benchmark, _resolve_ckpt
    models = real_models()
    log(f"benchmark-only: {len(models)} 个模型，对已有 checkpoint 补测速度+大小")
    out: list[dict] = []
    BENCH_JSON = REPO / "results" / "training" / "train_all_benchmark.json"
    MP = REPO / "results" / "training" / "metrics.json"

    def upsert_speed(run_id: str, speed: dict) -> None:
        """把 speed 回填到 metrics.json 的 run.metrics.speed。"""
        if not run_id or not MP.is_file():
            return
        d = json.load(open(MP))
        r = next((x for x in d.get("runs", []) if x.get("id") == run_id), None)
        if not r:
            return
        r.setdefault("metrics", {})
        r["metrics"]["speed"] = speed
        tmp = str(MP) + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
        os.replace(tmp, MP)

    for i, m in enumerate(models):
        mid = m["id"]
        run_id = find_trainall_run(mid)
        ckpt = _resolve_ckpt(mid, run_id) if run_id else _resolve_ckpt(mid, None)
        cfg_abs = resolve_cfg(mid, m["mmaction2_config"])
        ann = str(REPO / "datasets" / "pet_action_mammal_v0" / "annotation" / "val_public.txt")
        data_root = str(REPO / "datasets" / "pet_action_mammal_v0")
        if not ckpt:
            log(f"[{i+1}/{len(models)}] {mid}: 无 checkpoint，跳过")
            continue
        log(f"[{i+1}/{len(models)}] {mid}: bench ckpt={os.path.basename(ckpt)}")
        try:
            b = benchmark(cfg_abs, ckpt, ann, data_root, num_videos=5, device=f"cuda:{GPU}")
            b.update({"model": mid, "run_id": run_id})
            out.append(b)
            upsert_speed(run_id, {k: b[k] for k in ("latency_ms", "fps", "rtf", "gpu_mem_mb", "param_count_m", "ckpt_size_mb", "num_videos", "device") if k in b})
            log(f"  {mid}: latency={b.get('latency_ms')}ms fps={b.get('fps')} rtf={b.get('rtf')} params={b.get('param_count_m')}M ckpt={b.get('ckpt_size_mb')}MB")
        except Exception as e:
            out.append({"model": mid, "run_id": run_id, "error": str(e)})
            log(f"  {mid}: 失败 {e}")
        BENCH_JSON.parent.mkdir(parents=True, exist_ok=True)
        with open(str(BENCH_JSON) + ".tmp", "w") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        os.replace(str(BENCH_JSON) + ".tmp", BENCH_JSON)
    return 0


def main() -> int:
    if "--benchmark-only" in sys.argv:
        return benchmark_only()
    # --only a,b,c 只跑指定模型（补跑失败项）
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only="):
            only = set(a.split("=", 1)[1].split(","))
    models = real_models()
    if only:
        models = [m for m in models if m["id"] in only]
    log(f"共 {len(models)} 个模型，GPU{GPU} 串行，{EPOCHS}ep bs≤{BATCH}")
    summary: list[dict] = []
    for i, m in enumerate(models):
        mid = m["id"]
        cfg_abs = resolve_cfg(mid, m["mmaction2_config"])
        pretrained = os.path.join(CHECKPOINTS_DIR, mid, f"{mid}_pretrained.pth")
        has_pre = os.path.isfile(pretrained)
        lr = lr_for(mid)
        bs = 1 if mid in HEAVY_MODELS else BATCH
        run_id = f"trainall-{mid}-{int(time.time())}"
        args = [
            PYTHON, str(REPO / "scripts" / "train_model.py"),
            "--model-id", mid, "--dataset-id", DATASET, "--run-id", run_id,
            "--mmaction2-config", cfg_abs,
            "--epochs", str(EPOCHS), "--lr", str(lr), "--batch-size", str(bs),
            "--device", "cuda", "--num-classes", "7", "--vis-interval", "99", "--seed", "42",
        ]
        # videomae pet config 用 init_cfg，不传 --pretrained；其余传 --pretrained（load_from，head 形状不匹配被 strict=False 跳过）
        if has_pre and mid not in PET_CONFIGS:
            args += [f"--pretrained={pretrained}"]
        env = os.environ.copy()
        env["CUDA_VISIBLE_DEVICES"] = GPU
        env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
        log(f"[{i+1}/{len(models)}] {mid}: cfg={os.path.basename(cfg_abs)} pretrained={has_pre} lr={lr} bs={bs}")
        t0 = time.time()
        try:
            proc = subprocess.run(args, env=env, cwd=str(REPO), capture_output=True, text=True, timeout=5400)
            rc = proc.returncode
            err_tail = (proc.stderr or proc.stdout or "")[-400:]
        except subprocess.TimeoutExpired:
            rc = -1
            err_tail = "TIMEOUT"
        dt = time.time() - t0
        rm = read_run_metrics(run_id)
        best = rm.get("best_metric")
        speed = rm.get("speed")
        entry = {
            "model": mid, "run_id": run_id, "exit": rc, "best_metric": best,
            "duration_sec": round(dt), "lr": lr, "batch_size": bs,
            "error_tail": err_tail.strip() if rc != 0 else "",
        }
        if speed:
            entry["speed"] = speed
        summary.append(entry)
        save_summary(summary)
        sp = f" latency={speed.get('latency_ms')}ms fps={speed.get('fps')}" if speed else ""
        log(f"  {mid}: exit={rc} best={best}{sp} {dt:.0f}s")
    # 汇总排序
    done = [s for s in summary if s["best_metric"] is not None]
    done.sort(key=lambda s: s["best_metric"], reverse=True)
    log("=== 排行 ===")
    for s in done:
        log(f"  {s['best_metric']:.4f}  {s['model']}  ({s['duration_sec']}s)")
    failed = [s["model"] for s in summary if s["exit"] != 0]
    log(f"失败/无结果: {failed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
