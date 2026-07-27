#!/usr/bin/env python3
"""speed run：N 视频 × M 模型 → 标注视频 + 聚合 results.json。

视频输出走**固定格式**（按约定派生，不传 path arg）：
  results/speedrun/outputs/<model_id>/<video_stem>.mp4     # 帧叠 top-5
结果聚合：
  results/speedrun/results.json                            # per (model, video)

用法：
  python3 scripts/speedrun.py --videos a.mp4 b.mp4 --models all
  python3 scripts/speedrun.py --videos a.mp4 --models tsn-resnet50 i3d-resnet50 --device cuda:0
  python3 scripts/speedrun.py --videos a.mp4 --models tsn-resnet50 --force  # 重跑覆盖

权重默认用 ./checkpoints/<model_id>/<model_id>_pretrained.pth（已下好）。
标签默认 K400（models/mmaction2/tools/data/kinetics/label_map_k400.txt）。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import (
    CHECKPOINTS_DIR,
    SPEEDRUN_OUTPUTS_DIR,
    SPEEDRUN_RESULTS_JSON,
    resolve_mmaction2_config,
)
from server.routers.training import _MMACTION2_REGISTRY

# 默认 K400 标签（在 vendor 内）
_DEFAULT_K400_LABELS = os.path.join(
    REPO, "models", "mmaction2", "tools", "data", "kinetics", "label_map_k400.txt"
)

# 速度 run 不跑 quadruped 变体（那是四足数据集专用 config，不是独立模型）
_QUADRUPED_SUFFIX = "-quadruped"


def _models_by_ids(ids: list[str]) -> list[dict]:
    by_id = {m["id"]: m for m in _MMACTION2_REGISTRY}
    out = []
    for mid in ids:
        if mid not in by_id:
            print(f"[warn] 未知 model_id: {mid}（跳过）", file=sys.stderr)
            continue
        out.append(by_id[mid])
    return out


def _resolve_models(arg: list[str]) -> list[dict]:
    if not arg or arg == ["all"]:
        return [m for m in _MMACTION2_REGISTRY if not m["id"].endswith(_QUADRUPED_SUFFIX)]
    return _models_by_ids(arg)


def _pretrained_ckpt(model_id: str) -> str | None:
    p = os.path.join(CHECKPOINTS_DIR, model_id, f"{model_id}_pretrained.pth")
    return p if os.path.isfile(p) else None


def _load_results_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {"generated_at": None, "results": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and "results" in d:
            return d
    except (json.JSONDecodeError, OSError):
        pass
    return {"generated_at": None, "results": []}


def _save_results_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def main() -> int:
    parser = argparse.ArgumentParser(description="mmaction2 speed run：视频×模型 → 标注视频 + 结果")
    parser.add_argument("--videos", nargs="+", required=True, help="视频文件路径（至少一个）")
    parser.add_argument("--models", nargs="+", default=["all"], help='model_id 列表 或 "all"')
    parser.add_argument("--checkpoint", default="pretrained", help='"pretrained"（默认）或 checkpoint 路径')
    parser.add_argument("--labels", default=_DEFAULT_K400_LABELS, help="label_map 文件（默认 K400）")
    parser.add_argument("--device", default="cuda:0", help="cuda:0 / cpu")
    parser.add_argument("--out-dir", default=SPEEDRUN_OUTPUTS_DIR, help=f"标注视频根目录（默认 {SPEEDRUN_OUTPUTS_DIR}）")
    parser.add_argument("--results-json", default=SPEEDRUN_RESULTS_JSON, help=f"结果 JSON（默认 {SPEEDRUN_RESULTS_JSON}）")
    parser.add_argument("--force", action="store_true", help="重跑已存在的（默认跳过）")
    args = parser.parse_args()

    # 延迟 import：_infer 依赖 mmaction（只在 pet env 有）
    from scripts._infer import infer_and_annotate, load_labels
    from mmengine.config import Config

    labels = load_labels(args.labels)
    models = _resolve_models(args.models)
    if not models:
        print("[error] 没有可跑的模型", file=sys.stderr)
        return 1
    missing_ckpts = [m["id"] for m in models if args.checkpoint == "pretrained" and not _pretrained_ckpt(m["id"])]
    if missing_ckpts:
        print(f"[warn] 以下模型缺 pretrained checkpoint（跳过）：{missing_ckpts}", file=sys.stderr)
        models = [m for m in models if not (args.checkpoint == "pretrained" and not _pretrained_ckpt(m["id"]))]

    print(f"speed run: {len(models)} 模型 × {len(args.videos)} 视频 → {args.out_dir}")
    data = _load_results_json(args.results_json)
    results_by_id = {r["id"]: r for r in data.get("results", [])}
    failures: list[str] = []

    for m in models:
        model_id = m["id"]
        cfg_path = resolve_mmaction2_config(m["mmaction2_config"])
        ckpt = _pretrained_ckpt(model_id) if args.checkpoint == "pretrained" else args.checkpoint
        if not ckpt or not os.path.isfile(ckpt):
            print(f"[{model_id}] checkpoint 缺失：{ckpt}（跳过）")
            continue
        print(f"[{model_id}] cfg={cfg_path} ckpt={ckpt}")

        for video in args.videos:
            video_stem = Path(video).stem
            rid = f"speedrun-{model_id}-{video_stem}"
            out_video = os.path.join(args.out_dir, model_id, f"{video_stem}.mp4")
            rel_video = f"outputs/{model_id}/{video_stem}.mp4"  # 相对 SPEEDRUN_DIR

            # 跳过已存在（除非 --force）
            if os.path.isfile(out_video) and not args.force:
                print(f"  [{video_stem}] skip (exists)")
                if rid not in results_by_id:
                    results_by_id[rid] = {
                        "id": rid, "model_id": model_id, "video": video,
                        "checkpoint": ckpt, "metrics": {}, "output_video": rel_video,
                        "status": "skipped", "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                continue

            t0 = time.time()
            try:
                cfg = Config.fromfile(cfg_path)
                res = infer_and_annotate(
                    video, cfg, ckpt, labels,
                    out_video_path=out_video, device=args.device,
                )
                results_by_id[rid] = {
                    "id": rid, "model_id": model_id, "video": video, "checkpoint": ckpt,
                    "metrics": res, "output_video": rel_video, "status": "completed",
                    "gpu_mem_mb": res.get("gpu_mem_mb"),
                    "elapsed_s": round(time.time() - t0, 1),
                    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                print(f"  [{video_stem}] top1={res['top1_label']} ({res['top1_score']:.2f}) gpu={res.get('gpu_mem_mb')}MB → {out_video}")
            except Exception as e:
                results_by_id[rid] = {
                    "id": rid, "model_id": model_id, "video": video, "checkpoint": ckpt,
                    "metrics": {}, "output_video": rel_video if os.path.isfile(out_video) else None,
                    "status": "error", "error": str(e),
                    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                print(f"  [{video_stem}] ERROR: {e}")
                traceback.print_exc()
                failures.append(rid)

            # 每个 (model, video) 跑完即落盘（防长跑中途丢失）
            data = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "results": list(results_by_id.values())}
            _save_results_json(args.results_json, data)

    data = {"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "results": list(results_by_id.values())}
    _save_results_json(args.results_json, data)
    print(f"\nDone. {len(results_by_id)} results → {args.results_json}")
    if failures:
        print(f"Failed: {len(failures)} ({failures})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
