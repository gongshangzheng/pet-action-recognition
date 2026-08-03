"""预筛视频——用 decord 探测每个视频能否解码，剔除坏视频，输出过滤后的 val_list。

mmaction2 test loop 用 decord 解码，遇到坏视频会抛 DECORDError 整个 run 崩。
本脚本把 val_list 里 decord 打不开/读不到帧的视频剔除，写过滤后 list。

用法：
  python scripts/prefilter_videos.py \
    --ann-file ~/mnt/kinetics400/kinetics400_val_list_videos.txt \
    --data-root ~/mnt/kinetics400/videos_val \
    --out ~/mnt/kinetics400/kinetics400_val_list_filtered.txt \
    --decoder decord
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _probe_decord(path: str) -> bool:
    try:
        import decord
        vr = decord.VideoReader(path)
        return len(vr) > 0
    except Exception:
        return False


def _probe_cv2(path: str) -> bool:
    try:
        import cv2
        cap = cv2.VideoCapture(path)
        ok = cap.isOpened() and cap.get(cv2.CAP_PROP_FRAME_COUNT) > 0
        cap.release()
        return ok
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ann-file", required=True)
    ap.add_argument("--data-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--decoder", default="decord", choices=["decord", "cv2"])
    ap.add_argument("--limit", type=int, default=None, help="只筛前 N 条（测试用）")
    args = ap.parse_args()

    probe = _probe_decord if args.decoder == "decord" else _probe_cv2
    lines = open(args.ann_file).read().splitlines()
    if args.limit:
        lines = lines[: args.limit]
    print(f"[prefilter] {len(lines)} 条, decoder={args.decoder}, out={args.out}", flush=True)

    good = []
    bad = []
    t0 = time.time()
    for i, ln in enumerate(lines):
        parts = ln.strip().split()
        if len(parts) < 2:
            continue
        rel, lab = parts[0], parts[1]
        full = rel if os.path.isabs(rel) else os.path.join(args.data_root, rel)
        if not os.path.isfile(full):
            bad.append(ln)
            continue
        if probe(full):
            good.append(ln)
        else:
            bad.append(ln)
        if (i + 1) % 500 == 0:
            print(f"  [{i+1}/{len(lines)}] good={len(good)} bad={len(bad)} {time.time()-t0:.0f}s", flush=True)

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w") as f:
        f.write("\n".join(good) + "\n")
    print(f"\n[prefilter] done: good={len(good)} bad={len(bad)} ({len(bad)} 剔除) → {args.out}, {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
