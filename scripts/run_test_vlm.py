"""VLM 评测——用 Qwen3-VL-Plus 对 val_list 跑识别，写 test_results.json（同 mmaction2 shape）。

镜像 scripts/run_test.py，但不 subprocess tools/test.py；遍历 val_list 每视频调
scripts/vlm_infer.vlm_recognize，累计 correct/topk → top1/top5/mean1 + 速度 + 成本。
EvalResults.vue 零改显示（同 shape；metrics.cost 是新增字段，可选展示）。

用法：
  python scripts/run_test_vlm.py --run-id k400-vlm-smoke \
    --dataset-id kinetics400 --split val \
    --label-map ~/mnt/kinetics400/annotations/label_map_k400.txt \
    --ann-file ~/mnt/kinetics400/kinetics400_val_list_videos.txt \
    --data-root ~/mnt/kinetics400/videos_val --num-videos 200
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from server.config import TRAINING_DIR  # noqa: E402
from scripts.run_test import load_results, save_results, resolve_test_paths  # noqa: E402
from scripts._infer import load_labels  # noqa: E402
from scripts.vlm_infer import vlm_recognize  # noqa: E402

RESULTS_JSON = os.path.join(TRAINING_DIR, "test_results.json")


def _video_duration(video_path: str) -> float:
    """视频时长（秒），cv2 读 frame_count/fps。"""
    import cv2
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    n = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return (n / fps) if fps > 0 and n > 0 else 0.0


def _read_val_list(ann_file: str, data_root: str, n: int | None) -> list[tuple[str, int]]:
    """读 ann_file → [(abs_video_path, label_id), ...]，前 n 条（n=None 全量）。"""
    out = []
    with open(ann_file) as f:
        for ln in f:
            parts = ln.strip().split()
            if len(parts) < 2:
                continue
            rel, lab = parts[0], int(parts[1])
            full = rel if os.path.isabs(rel) else os.path.join(data_root, rel)
            if os.path.isfile(full):
                out.append((full, lab))
            if n and len(out) >= n:
                break
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="VLM(Qwen3-VL-Plus) 评测 wrapper")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--dataset-id", default="kinetics400")
    ap.add_argument("--split", default="val")
    ap.add_argument("--label-map", required=True, help="label_map.txt（每行一个类名，index=类id）")
    ap.add_argument("--ann-file", default=None, help="覆盖 ann_file（K400 用）")
    ap.add_argument("--data-root", default=None, help="覆盖 data_prefix.video")
    ap.add_argument("--num-videos", type=int, default=None, help="子集大小（None=全量）")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--max-pixels", type=int, default=640 * 32 * 32)
    ap.add_argument("--min-pixels", type=int, default=4 * 32 * 32)
    ap.add_argument("--model-name", default="qwen3-vl-plus")
    ap.add_argument("--device", default="cuda", help="占位（VLM 走云端，不占本地 GPU）")
    ap.add_argument("--checkpoint", default="<VLM>", help="占位字段（VLM 无 checkpoint）")
    ap.add_argument("--mmaction2-config", default="vlm", help="占位（写进 result.model 字段）")
    args = ap.parse_args()

    ann = args.ann_file
    videos_root = args.data_root
    if not ann or not videos_root:
        a2, v2 = resolve_test_paths(args.dataset_id, args.split)
        ann = ann or a2
        videos_root = videos_root or v2
    if not ann or not videos_root:
        print(f"[error] ann_file/data_root 未指定且 {args.dataset_id}/{args.split} 无默认")
        return 1

    labels = load_labels(args.label_map)
    val = _read_val_list(ann, videos_root, args.num_videos)
    print(f"[vlm-eval] {len(val)} 视频, {len(labels)} 类, model={args.model_name}", flush=True)
    if not val:
        print("[error] 无视频（ann_file/data_root 不匹配？）")
        return 1

    # 累计
    n = len(val)
    top1_correct = 0
    top5_correct = 0
    per_class_correct: dict[int, int] = {}
    per_class_top5_correct: dict[int, int] = {}
    per_class_total: dict[int, int] = {}
    latencies, durations = [], []
    tot_in = tot_out = 0
    tot_cost = 0.0
    responses = []
    t_start = time.time()

    for i, (vpath, gt_id) in enumerate(val):
        r = vlm_recognize(vpath, labels, fps=args.fps, max_pixels=args.max_pixels,
                          min_pixels=args.min_pixels, model_name=args.model_name)
        if r.get("error") or not r.get("top1_label"):
            print(f"  [{i+1}/{n}] {os.path.basename(vpath)} → ERR {r.get('error','')[:60]}", flush=True)
            per_class_correct.setdefault(gt_id, 0)
            per_class_top5_correct.setdefault(gt_id, 0)
            per_class_total[gt_id] = per_class_total.get(gt_id, 0) + 1
            continue
        # top1/top5 对比 GT
        top1_label = r["top1_label"]
        top5_labels = [lbl for lbl, _ in r["top5"]]
        gt_name = labels[gt_id] if gt_id < len(labels) else ""
        t1_ok = _norm_eq(top1_label, gt_name)
        t5_ok = any(_norm_eq(l, gt_name) for l in top5_labels)
        if t1_ok:
            top1_correct += 1
        if t5_ok:
            top5_correct += 1
        per_class_correct[gt_id] = per_class_correct.get(gt_id, 0) + (1 if t1_ok else 0)
        per_class_top5_correct[gt_id] = per_class_top5_correct.get(gt_id, 0) + (1 if t5_ok else 0)
        per_class_total[gt_id] = per_class_total.get(gt_id, 0) + 1

        latencies.append(r.get("duration_sec", 0))
        tot_in += r.get("input_tokens", 0)
        tot_out += r.get("output_tokens", 0)
        tot_cost += r.get("cost_cny", 0)
        vd = _video_duration(vpath)
        if vd > 0:
            durations.append(vd)
        responses.append({"video": os.path.basename(vpath), "gt": gt_name, "top1": top1_label, "top5": top5_labels})
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{n}] acc≈{top1_correct/(i+1):.3f} cost≈{tot_cost:.4f}元", flush=True)

    top1_acc = top1_correct / n if n else 0
    top5_acc = top5_correct / n if n else 0
    # mean per-class top1/top5（抗类别不均衡）
    cls_accs = [per_class_correct[c] / per_class_total[c]
                for c in per_class_total if per_class_total[c] > 0]
    mean1 = sum(cls_accs) / len(cls_accs) if cls_accs else 0
    cls_top5 = [per_class_top5_correct[c] / per_class_total[c]
                for c in per_class_total if per_class_total[c] > 0]
    mean5 = sum(cls_top5) / len(cls_top5) if cls_top5 else 0

    total_time = sum(latencies)
    metrics = {
        "top1_acc": round(top1_acc, 4),
        "top5_acc": round(top5_acc, 4),
        "mean1_acc": round(mean1, 4),
        "mean5_acc": round(mean5, 4),
        "speed": {
            "latency_ms": round(total_time / n * 1000, 1) if n else None,
            "fps": round(n / total_time, 2) if total_time > 0 else None,
            "rtf": round(total_time / sum(durations), 3) if durations else None,
            "gpu_mem_mb": None,
            "param_count_m": None,
            "ckpt_size_mb": None,
        },
        "cost": {
            "input_tokens": tot_in,
            "output_tokens": tot_out,
            "total_tokens": tot_in + tot_out,
            "cost_cny": round(tot_cost, 4),
            "num_videos": n,
        },
    }
    result = {
        "id": args.run_id,
        "model": args.model_name,
        "dataset": args.dataset_id,
        "split": args.split,
        "checkpoint": args.checkpoint,
        "metrics": metrics,
        "stdout_tail": f"VLM eval done: top1={top1_acc:.4f} top5={top5_acc:.4f} mean1={mean1:.4f} cost={tot_cost:.4f}元 ({n} videos)",
        "status": "completed",
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    data = load_results()
    data["results"] = [r for r in data.get("results", []) if r.get("id") != args.run_id]
    data["results"].append(result)
    data["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    save_results(data)
    print(f"\n=== VLM eval done (n={n}, {time.time()-t_start:.0f}s) ===")
    print(f"  top1={top1_acc:.4f} top5={top5_acc:.4f} mean1={mean1:.4f}")
    print(f"  latency={metrics['speed']['latency_ms']}ms fps={metrics['speed']['fps']} rtf={metrics['speed']['rtf']}")
    print(f"  cost={tot_cost:.4f}元 (in={tot_in} out={tot_out} tokens)")
    return 0


def _norm_eq(a: str, b: str) -> bool:
    """类名归一化相等（移植自 speedrun._matches）。"""
    from scripts.vlm_infer import _norm_tokens
    return _norm_tokens(a) == _norm_tokens(b)


if __name__ == "__main__":
    sys.exit(main())
