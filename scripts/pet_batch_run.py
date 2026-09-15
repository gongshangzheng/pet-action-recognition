"""全量批处理驱动：34 段白天视频 → 运动校正轨迹 + 跟随视角视频。

batch-followcam-extraction 任务 1.5。逐段执行 pet_detect_track → make_followcam，
单段失败跳过不阻塞；进度逐段追加 batch_progress.jsonl，结束写 batch_summary.json。

用法（pet，plf 环境）：
  nohup python scripts/pet_batch_run.py --list ~/daytime_list.txt \
      --root ~/results/batch > ~/batch_run.log 2>&1 &
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

PY = "/home/wyy/miniconda3/envs/plf/bin/python"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--root", default="/home/wyy/results/batch")
    ap.add_argument("--script-dir", default="/home/wyy/pet-action-recognition/scripts")
    ap.add_argument("--gpu", default="0")
    args = ap.parse_args()

    videos = [l.strip() for l in open(args.list) if l.strip()]
    os.makedirs(args.root, exist_ok=True)
    log_path = os.path.join(args.root, "batch_progress.jsonl")
    results = []
    print(f"BATCH START {len(videos)} segments", flush=True)

    for i, v in enumerate(videos):
        seg = os.path.basename(v).replace(".mp4", "")
        out = os.path.join(args.root, seg)
        os.makedirs(out, exist_ok=True)
        t0 = time.time()
        rec: dict = {"seg": seg, "video": v, "status": "started",
                     "t": time.strftime("%F %T")}

        def log() -> None:
            with open(log_path, "a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        log()
        r1 = subprocess.run(
            f"CUDA_VISIBLE_DEVICES={args.gpu} {PY} "
            f"{args.script_dir}/pet_detect_track.py --video '{v}' --out '{out}'",
            shell=True, capture_output=True, text=True)
        if r1.returncode != 0:
            rec.update(status="detect_failed", err=r1.stderr[-400:],
                       secs=round(time.time() - t0, 1))
            log()
            results.append(rec)
            print(f"[{i+1}/{len(videos)}] {seg}: detect_failed", flush=True)
            continue
        r2 = subprocess.run(
            f"{PY} {args.script_dir}/make_followcam.py --video '{v}' "
            f"--track '{out}/track.json' --out '{out}'",
            shell=True, capture_output=True, text=True)
        rec["status"] = "ok" if r2.returncode == 0 else "followcam_failed"
        tj = os.path.join(out, "track.json")
        if os.path.exists(tj):
            d = json.load(open(tj))
            rec["frames"] = d["frames"]
            rec["interp"] = d["interpolated_ratio"]
            rec["corrected"] = d["motion_correct_ratio"]
            rec["det_rate"] = round(
                len(d.get("sampled_detections", {}))
                / max(1, -(-d["frames"] // d.get("sample_stride", 10))), 3)
        rec["secs"] = round(time.time() - t0, 1)
        log()
        results.append(rec)
        print(f"[{i+1}/{len(videos)}] {seg}: {rec['status']} "
              f"det={rec.get('det_rate')} interp={rec.get('interp')} "
              f"({rec['secs']}s)", flush=True)

    with open(os.path.join(args.root, "batch_summary.json"), "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"BATCH DONE {ok}/{len(videos)} ok", flush=True)


if __name__ == "__main__":
    main()
