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
import subprocess
import sys
import time
import traceback
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import (
    CHECKPOINTS_DIR,
    MMACTION2_DIR,
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


def _norm_tokens(s: str) -> tuple:
    """归一化类名为排序 token 组：拆 camelCase + 拆非字母数字 + lowercase + 排序。
    用于匹配 GT（UCF101 'PlayingGuitar'）与 pred（K400 'playing guitar'）等。"""
    s = re.sub(r'(.)([A-Z][a-z])', r'\1 \2', s)   # PlayingGuitar → Playing Guitar
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)     # camelCase 边界
    toks = [t for t in re.split(r'[^a-z0-9]+', s.lower()) if t]
    return tuple(sorted(toks))


def _matches(gt: str | None, pred: str | None) -> bool | None:
    """GT vs pred 类名是否匹配（token-set 归一化）。gt 为 None → None（N/A）。"""
    if not gt or not pred:
        return None
    return _norm_tokens(gt) == _norm_tokens(pred)


def _extract_cover(video_path: str, cover_path: str) -> None:
    """从视频中间帧提取封面图（JPG，所有模型共用同一张）。"""
    import cv2
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total > 2:
        cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ok, frame = cap.read()
    cap.release()
    if ok and frame is not None:
        cv2.imwrite(cover_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 80])


def _video_duration(video_path: str) -> float:
    """视频时长（秒）= frame_count / fps；读取失败返回 0。"""
    import cv2
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return 0.0
    fc = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    cap.release()
    if not fps or fps <= 0:
        return 0.0
    return (fc or 0.0) / fps


def _gpu_util() -> float | None:
    """采样 GPU 利用率（%）。nvidia-smi 不可用返回 None。"""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            return None
        vals = [float(x) for x in proc.stdout.strip().splitlines() if x.strip() != ""]
        if not vals:
            return None
        return round(sum(vals) / len(vals), 1)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def _models_by_ids(ids: list[str]) -> list[dict]:
    by_id = {m["id"]: m for m in _MMACTION2_REGISTRY}
    out = []
    for mid in ids:
        if mid not in by_id:
            print(f"[warn] 未知 model_id: {mid}（跳过）", file=sys.stderr)
            continue
        out.append(by_id[mid])
    return out


def _parse_custom(specs: list[str]) -> dict[str, dict]:
    """解析 --custom model_id=config_path:ckpt_path（可重复）→ registry 同形条目。"""
    out: dict[str, dict] = {}
    for spec in specs or []:
        try:
            mid, rest = spec.split("=", 1)
            config, ckpt = rest.rsplit(":", 1)
        except ValueError:
            print(f"[warn] --custom 格式错误（应为 model_id=config:ckpt）：{spec}", file=sys.stderr)
            continue
        mid, config, ckpt = mid.strip(), config.strip(), ckpt.strip()
        if not (mid and config and ckpt):
            print(f"[warn] --custom 字段不全：{spec}", file=sys.stderr)
            continue
        if not os.path.isfile(config):
            print(f"[warn] --custom config 不存在：{config}（跳过 {mid}）", file=sys.stderr)
            continue
        if not os.path.isfile(ckpt):
            print(f"[warn] --custom checkpoint 不存在：{ckpt}（跳过 {mid}）", file=sys.stderr)
            continue
        out[mid] = {"id": mid, "config": config, "checkpoint": ckpt, "label_map": None}
    return out


def _load_ann_gt(ann_file: str, label_map: list[str]) -> dict[str, str]:
    """ann_file（raw label：<video_path> <label_idx>）→ {video_stem: 类名}。"""
    gt: dict[str, str] = {}
    with open(ann_file, encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2:
                continue
            stem = Path(parts[0]).stem
            try:
                idx = int(parts[1])
            except ValueError:
                continue
            if 0 <= idx < len(label_map):
                gt[stem] = label_map[idx]
    return gt


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
    parser.add_argument("--models", nargs="+", default=None, help='model_id 列表 或 "all"（默认：有 --custom 时仅跑 custom，否则 all）')
    parser.add_argument("--checkpoint", default="pretrained", help='"pretrained"（默认）或 checkpoint 路径')
    parser.add_argument("--labels", default=_DEFAULT_K400_LABELS, help="label_map 文件（默认 K400）")
    parser.add_argument("--device", default="cuda:0", help="cuda:0 / cpu")
    parser.add_argument("--out-dir", default=SPEEDRUN_OUTPUTS_DIR, help=f"标注视频根目录（默认 {SPEEDRUN_OUTPUTS_DIR}）")
    parser.add_argument("--results-json", default=SPEEDRUN_RESULTS_JSON, help=f"结果 JSON（默认 {SPEEDRUN_RESULTS_JSON}）")
    parser.add_argument("--force", action="store_true", help="重跑已存在的（默认跳过）")
    parser.add_argument("--run-name", default=None, help="运行批次名（Descriptor），写入每条结果；缺省自动生成 run-{YYYYMMDD-HHmm}")
    parser.add_argument("--custom", action="append", default=[], metavar="MODEL_ID=CONFIG:CKPT",
                        help="自定义模型（可重复）：绕过 registry，指定 config+checkpoint（如微调权重）")
    parser.add_argument("--ann-file", default=None, help="GT 标注文件（raw label：<video_path> <label_idx>），按 stem 匹配")
    parser.add_argument("--label-map", default=None, help="类名表（配合 --ann-file / --custom，每行一个类名）")
    args = parser.parse_args()

    run_name = args.run_name or f"run-{time.strftime('%Y%m%d-%H%M')}"

    # 延迟 import：_infer 依赖 mmaction（只在 pet env 有）
    from scripts._infer import infer_and_annotate, load_labels
    from mmengine.config import Config

    # per-model label_map 缓存（非 K400 模型用自己的 label_map）
    _label_cache: dict[str, list[str]] = {}
    def _labels_for(model_entry):
        lm = model_entry.get("label_map", args.labels)
        if not os.path.isabs(lm):
            lm = os.path.join(str(REPO), lm)
        if lm not in _label_cache:
            _label_cache[lm] = load_labels(lm)
        return _label_cache[lm]

    # 类名表：--label-map 优先（供 ann_file 索引 + custom 模型标注），否则回退 K400 默认
    global_label_map = args.label_map or args.labels
    if not os.path.isabs(global_label_map):
        global_label_map = os.path.join(str(REPO), global_label_map)

    # --custom 优先：单独传 --custom（未显式传 --models）时仅跑 custom 模型
    custom_models = _parse_custom(args.custom)
    if custom_models and not args.models:
        models = list(custom_models.values())
    else:
        models = _resolve_models(args.models or ["all"])
    # --custom 与 --models 混用：同名 id 覆盖 registry（warn）
    for mid, entry in custom_models.items():
        entry["label_map"] = global_label_map  # custom 模型统一用 --label-map（微调模型类表）
        dup = [i for i, m in enumerate(models) if m["id"] == mid]
        if dup:
            print(f"[warn] --custom {mid} 覆盖同名 registry 模型", file=sys.stderr)
            models[dup[0]] = entry
        else:
            models.append(entry)
    if not models:
        print("[error] 没有可跑的模型", file=sys.stderr)
        return 1
    missing_ckpts = [m["id"] for m in models
                     if args.checkpoint == "pretrained" and "checkpoint" not in m
                     and not _pretrained_ckpt(m["id"])]
    if missing_ckpts:
        print(f"[warn] 以下模型缺 pretrained checkpoint（跳过）：{missing_ckpts}", file=sys.stderr)
        models = [m for m in models
                  if not (args.checkpoint == "pretrained" and "checkpoint" not in m
                          and not _pretrained_ckpt(m["id"]))]

    # GT：--ann-file 优先（stem → 类名），未命中回退父目录派生（UCF101）
    ann_gt: dict[str, str] = {}
    if args.ann_file:
        af = args.ann_file if os.path.isabs(args.ann_file) else os.path.join(str(REPO), args.ann_file)
        if not os.path.isfile(af):
            print(f"[error] --ann-file 不存在: {af}", file=sys.stderr)
            return 1
        ann_gt = _load_ann_gt(af, load_labels(global_label_map))
        print(f"GT from ann_file: {len(ann_gt)} 条 (label_map={os.path.basename(global_label_map)})")

    def _gt_for(video: str):
        stem = Path(video).stem
        if stem in ann_gt:
            return ann_gt[stem]
        return Path(video).parent.name if "ucf101" in video.lower() else None

    print(f"speed run: {len(models)} 模型 × {len(args.videos)} 视频 → {args.out_dir}")
    data = _load_results_json(args.results_json)
    results_by_id = {r["id"]: r for r in data.get("results", [])}
    failures: list[str] = []

    # 提取封面图（每个视频一张，所有模型共用）
    covers_dir = os.path.join(args.out_dir, "covers")
    os.makedirs(covers_dir, exist_ok=True)
    video_covers: dict[str, str] = {}
    for v in args.videos:
        stem = Path(v).stem
        cover_rel = f"covers/{stem}.jpg"
        cover_path = os.path.join(args.out_dir, cover_rel)
        if not os.path.isfile(cover_path):
            try:
                _extract_cover(v, cover_path)
            except Exception as e:
                print(f"[warn] 封面提取失败 {stem}: {e}")
        if os.path.isfile(cover_path):
            video_covers[stem] = cover_rel

    for m in models:
        model_id = m["id"]
        # --custom 模型自带 config/checkpoint；registry 模型走 mmaction2_config + --checkpoint
        if "config" in m and "checkpoint" in m:
            cfg_path = m["config"]
            ckpt = m["checkpoint"]
        else:
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
            rel_video = f"{model_id}/{video_stem}.mp4"  # 相对 SPEEDRUN_OUTPUTS_DIR（服务端点根），不含 outputs/ 前缀

            # 跳过已存在（除非 --force）
            if os.path.isfile(out_video) and not args.force:
                print(f"  [{video_stem}] skip (exists)")
                if rid not in results_by_id:
                    results_by_id[rid] = {
                        "id": rid, "model_id": model_id, "video": video,
                        "checkpoint": ckpt, "metrics": {}, "output_video": rel_video,
                        "status": "skipped", "cover_image": video_covers.get(video_stem),
                        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                continue

            t0 = time.time()
            gt_label = _gt_for(video)
            try:
                if m.get("type") == "detection":
                    # 检测模型：subprocess demo_spatiotemporal_det.py（不走 inference_recognizer）
                    demo_script = os.path.join(MMACTION2_DIR, "demo", "demo_spatiotemporal_det.py")
                    abs_video = video if os.path.isabs(video) else os.path.join(str(REPO), video)
                    abs_out = out_video if os.path.isabs(out_video) else os.path.join(str(REPO), out_video)
                    os.makedirs(os.path.dirname(abs_out), exist_ok=True)
                    det_cfg = m.get("det_config", "")
                    det_ckpt = m.get("det_checkpoint", "")
                    if not os.path.isabs(det_ckpt):
                        det_ckpt = os.path.join(str(REPO), det_ckpt)
                    lm = m.get("label_map", _DEFAULT_K400_LABELS)
                    if not os.path.isabs(lm):
                        lm = os.path.join(str(REPO), lm)
                    gpu_before = _gpu_util()
                    vdur = _video_duration(video)
                    cmd = [
                        sys.executable, demo_script,
                        abs_video, abs_out,
                        "--config", cfg_path,
                        "--checkpoint", ckpt,
                        "--det-config", det_cfg,
                        "--det-checkpoint", det_ckpt,
                        "--label-map", lm,
                        "--device", args.device,
                    ]
                    proc = subprocess.run(cmd, cwd=str(MMACTION2_DIR), capture_output=True, text=True, timeout=300)
                    status = "completed" if proc.returncode == 0 else "error"
                    elapsed_s = round(time.time() - t0, 1)
                    gpu_after = _gpu_util()
                    gpu_avg = round((gpu_before + gpu_after) / 2, 1) if gpu_before is not None and gpu_after is not None else None
                    rtf = round(elapsed_s / vdur, 2) if vdur > 0 else None
                    results_by_id[rid] = {
                        "id": rid, "model_id": model_id, "video": video, "checkpoint": ckpt,
                        "run_name": run_name,
                        "gt_label": gt_label, "correct": None,
                        "metrics": {"type": "detection", "note": "annotated video has person boxes + AVA action labels"},
                        "output_video": rel_video if os.path.isfile(abs_out) else None,
                        "status": status,
                        "elapsed_s": elapsed_s,
                        "gpu_avg_util": gpu_avg,
                        "rtf": rtf,
                        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    print(f"  [{video_stem}] detection {'OK' if status == 'completed' else 'FAIL'} → {abs_out}")
                    if status == "error":
                        print(f"    stderr: {proc.stderr[-500:] if proc.stderr else '(empty)'}")
                        failures.append(rid)
                else:
                    # 分类模型：inference_recognizer + cv2 margin 叠字
                    cfg = Config.fromfile(cfg_path)
                    gpu_before = _gpu_util()
                    vdur = _video_duration(video)
                    res = infer_and_annotate(
                        video, cfg, ckpt, _labels_for(m),
                        out_video_path=out_video, device=args.device,
                        gt_label=gt_label,
                    )
                    elapsed_s = round(time.time() - t0, 1)
                    gpu_after = _gpu_util()
                    gpu_avg = round((gpu_before + gpu_after) / 2, 1) if gpu_before is not None and gpu_after is not None else None
                    rtf = round(elapsed_s / vdur, 2) if vdur > 0 else None
                    results_by_id[rid] = {
                        "id": rid, "model_id": model_id, "video": video, "checkpoint": ckpt,
                        "run_name": run_name,
                        "gt_label": gt_label,
                        "correct": _matches(gt_label, res["top1_label"]),
                        "metrics": res, "output_video": rel_video, "status": "completed",
                        "gpu_mem_mb": res.get("gpu_mem_mb"),
                        "elapsed_s": elapsed_s,
                        "gpu_avg_util": gpu_avg,
                        "rtf": rtf,
                        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    }
                    print(f"  [{video_stem}] GT={gt_label} top1={res['top1_label']} ({res['top1_score']:.2f}) gpu={res.get('gpu_mem_mb')}MB rtf={rtf} util={gpu_avg}% → {out_video}")
            except Exception as e:
                results_by_id[rid] = {
                    "id": rid, "model_id": model_id, "video": video, "checkpoint": ckpt,
                    "run_name": run_name,
                    "metrics": {}, "output_video": rel_video if os.path.isfile(out_video) else None,
                    "status": "error", "error": str(e),
                    "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                }
                print(f"  [{video_stem}] ERROR: {e}")
                traceback.print_exc()
                failures.append(rid)

            # 封面图（所有模型共用同一张）
            if rid in results_by_id:
                results_by_id[rid].setdefault("cover_image", video_covers.get(video_stem))

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
