#!/usr/bin/env python3
"""RTMDet 独立交叉验证：与 YOLO11 同样的 cats 79 段，用 COCO cat(15) 独立观察
   在时间轴标注段内的检出分化模式。两模型一致 → "段内有猫，形态决定检出" 钉死。

   用 pet conda env: 含 mmpose/mmdet，已装 RTMDet COCO 权重。
"""
from __future__ import annotations
import argparse, json, glob
from pathlib import Path
import cv2
import numpy as np


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--videos-root", default="/home/wyy/mnt/cats")
    p.add_argument("--output-dir", default="/home/wyy/pet-action-recognition/results/detection/zeroshot_cats/rtmdet_cross")
    p.add_argument("--det-cfg", default="checkpoints/ap10k/rtmdet_m_8xb32-300e_coco.py")
    p.add_argument("--det-ckpt", default="checkpoints/ap10k/rtmdet_m_8xb32-300e_coco_20220719_112220-229f527c.pth")
    p.add_argument("--device", default="cuda:0")
    p.add_argument("--frame-interval", type=float, default=3.0)
    p.add_argument("--conf", type=float, default=0.30)
    p.add_argument("--cat-class", type=int, default=15, help="COCO cat 索引")
    return p.parse_args()


def find_videos(root: Path):
    out = []
    for sub in sorted(root.iterdir()):
        if sub.is_dir() and sub.name.startswith("dataset_"):
            out.extend(sorted(sub.glob("event_*.mp4")))
    return out


def load_annotations(root: Path):
    """复现 yolo11_zeroshot_audit 的标注载入（匹配规则必须完全一致才能对比）。"""
    import re
    from collections import defaultdict
    annotations = defaultdict(list)
    for sub in root.glob("annotation_*"):
        if not sub.is_dir(): continue
        for jf in sub.glob("*.json"):
            for item in json.load(open(jf)):
                vp = item.get("data", {}).get("video", "")
                if not vp: continue
                base = vp.split("/")[-1]
                fname = base.split("-", 1)[1] if "-" in base else base
                if not fname.startswith("event_"): continue
                for ann in item.get("annotations", []):
                    for res in ann.get("result", []):
                        val = res.get("value", {})
                        for rng in val.get("ranges", []):
                            for lbl in val.get("timelinelabels", []):
                                annotations[fname].append((int(rng["start"]), int(rng["end"]), lbl.split("/")[-1]))
    return annotations


def main():
    args = parse_args()
    from mmdet.apis import init_detector, inference_detector
    from mmengine.registry import init_default_scope
    init_default_scope("mmdet")

    repo = Path("/home/wyy/pet-action-recognition")
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"加载 RTMDet {args.det_cfg.split('/')[-1]}")
    det_model = init_detector(args.det_cfg, args.det_ckpt, device=args.device)

    root = Path(args.videos_root)
    videos = find_videos(root)
    annotations = load_annotations(root)
    print(f"videos: {len(videos)} | annotated keys: {len(annotations)}")

    # 统计：每个视频抽帧数 = round(fps * frame_interval)，至少 8 帧（保证 night/day 各组样本够）
    for i, v in enumerate(videos):
        anns = annotations.get(v.name, [])
        cap = cv2.VideoCapture(str(v)); fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); cap.release()
        step = max(1, round(fps * args.frame_interval))
        sampled_frames = list(range(0, n, step))
        if len(sampled_frames) > 60:
            # 上限 60 帧/视频，控制总推理量到 ~4700 帧
            idx = np.linspace(0, n - 1, 60).astype(int)
            sampled_frames = sorted(set(idx.tolist()))

        records = []
        cap = cv2.VideoCapture(str(v))
        for fi in sampled_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, fi); ok, frame = cap.read()
            if not ok: continue
            res = inference_detector(det_model, frame)
            # res.pred_instances: 含 labels (COCO id) 和 scores
            labels = res.pred_instances.labels.cpu().numpy().tolist()
            scores = res.pred_instances.scores.cpu().numpy().tolist()
            cat_max = 0.0
            for lbl, sc in zip(labels, scores):
                if lbl == args.cat_class and sc >= args.conf:
                    cat_max = max(cat_max, sc)
            records.append({"f": fi, "cat": round(cat_max, 3)})
        cap.release()
        with open(out_dir / f"{v.stem}_rtmdet.json", "w") as f:
            json.dump({"video": v.name, "n_frames": n, "fps": round(fps, 2),
                       "frames": records}, f)
        if (i + 1) % 10 == 0 or i + 1 == len(videos):
            print(f"[{i+1}/{len(videos)}] {v.name} ({len(records)} frames)")

    # 段内交叉分析（与 YOLO 完全相同的分母与口径）
    in_det = in_tot = out_det = out_tot = 0
    per_lbl = {}
    for fj in sorted(out_dir.glob("*_rtmdet.json")):
        d = json.load(open(fj))
        anns = annotations.get(d["video"], [])
        for fr in d["frames"]:
            inside = any(a <= fr["f"] <= b for a, b, _ in anns)
            if inside:
                in_tot += 1; in_det += (fr["cat"] > 0)
                for a, b, l in anns:
                    if a <= fr["f"] <= b:
                        per_lbl.setdefault(l, [0, 0]); per_lbl[l][1] += 1
                        per_lbl[l][0] += (fr["cat"] > 0)
            else:
                out_tot += 1; out_det += (fr["cat"] > 0)

    print("\n===== RTMDet cat 类（COCO 15）段内交叉 =====")
    print(f"  标注段内整体: {in_det}/{in_tot} = {in_det/max(1,in_tot):.1%}")
    print(f"  标注段外:     {out_det}/{out_tot} = {out_det/max(1,out_tot):.1%}")
    for l, (d, t) in sorted(per_lbl.items()):
        print(f"    {l:24s}: {d}/{t} = {d/max(1,t):.1%}")
    json.dump({"in": [in_det, in_tot], "out": [out_det, out_tot],
               "per_lbl": {l: [d, t] for l, (d, t) in per_lbl.items()}},
              open(out_dir / "rtmdet_cross.json", "w"))


if __name__ == "__main__":
    main()