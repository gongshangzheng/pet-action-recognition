#!/usr/bin/env python3
"""多宠物跟踪正式入口（multi-pet-sort-tracking）。

读 cat-crop-detection-v2 检测缓存，跑物种分实例 OC-SORT（use_byte），
把逐锚点轨迹写入独立输出目录。产物 schema 见 TRACKING_SCHEMA。

用法（本地，零 GPU）：
    python3 scripts/track_multi_pet.py \
        --detections results/tracking_eval_20261107/sample_detections/*.json \
        --out results/tracking_eval_20261107/tracks_v1

产物：
    <out>/<stem>.track.json   单视频轨迹（含输入指纹与跟踪参数）
    <out>/manifest.json       本批输入 sha256 与参数指纹
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from petlib.tracking.anchors import load_anchor_sequence  # noqa: E402
from petlib.tracking.oc_sort import OCSortTracker  # noqa: E402
from petlib.tracking.species_split import (  # noqa: E402
    SPECIES_ID_OFFSET,
    SpeciesSplitTracker,
)

TRACKING_SCHEMA = "multi-pet-tracking-v1"

# design 4.5：单流关联下，物种一致性低于此比例的轨迹标记为“物种存疑”
SPECIES_CONSISTENCY_MIN = 0.80

# design 4.7：生命周期按锚点数标定。3Hz 锚点下 max_age=8 ≈ 2.7s coast。
DEFAULT_PARAMS = {
    "min_conf": 0.10,       # 低于缓存 box_threshold=0.3 的候选不存在，此处不二次过滤
    "det_thresh": 0.10,     # 关联门放低，依赖方向代价（design 4.7）
    "max_age": 8,
    "min_hits": 2,
    "iou_threshold": 0.2,   # IoU 门放低，不硬卡（design 4.7）
    "delta_t": 3,
    "inertia": 0.2,
    "use_byte": True,
}


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def species_of(track_id: int) -> str:
    return "cat" if track_id < SPECIES_ID_OFFSET else "dog"


def _box_iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def track_video(detection_path: Path, params: dict, association: str = "species_split") -> dict:
    seq = load_anchor_sequence(detection_path)
    if association == "species_split":
        tracker = SpeciesSplitTracker(lambda cfg: OCSortTracker(**cfg), params)
    elif association == "single":
        # design 4.5（2026-11-07 修订）：单流关联，物种不再硬分实例
        tracker = OCSortTracker(**params)
    else:
        raise ValueError(f"unknown association mode: {association}")
    for frame, dets in zip(seq.frames, seq.detections, strict=True):
        tracker.update(dets, frame)
    tracks = tracker.finalize()

    # 物种元数据（design 4.5）：每个错点取与轨迹框 IoU 最大的检测，按物种多数投票
    dets_by_frame = dict(zip(seq.frames, seq.detections, strict=True))
    track_rows = []
    anchors_out: dict[str, list] = {}
    for tr in tracks:
        votes: dict[str, int] = {}
        points = []
        for p in tr.boxes:
            best = max(dets_by_frame.get(p.frame, []),
                       key=lambda d: _box_iou(d.box, p.box), default=None)
            if best is not None:
                votes[best.cls] = votes.get(best.cls, 0) + 1
            points.append({"frame": p.frame, "box": list(p.box), "conf": round(p.conf, 6)})

        if association == "species_split":
            # 硬分实例下物种由流决定，一致性恒为 1（保留基线产物可比性）
            species, consistency = species_of(tr.track_id), 1.0
        else:
            total = sum(votes.values())
            species = "unknown"
            if votes:
                species = sorted(votes.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
            consistency = round(votes.get(species, 0) / total, 4) if total else 0.0

        track_rows.append(
            {
                "track_id": tr.track_id,
                "species": species,
                "species_consistency": consistency,
                "species_flagged": consistency < SPECIES_CONSISTENCY_MIN,
                "state": "confirmed" if len(tr.boxes) >= params["min_hits"] else "tentative",
                "n_anchors": len(tr.boxes),
                "first_frame": tr.boxes[0].frame,
                "last_frame": tr.boxes[-1].frame,
                "points": points,
            }
        )
        for p in tr.boxes:
            anchors_out.setdefault(str(p.frame), []).append(
                {
                    "track_id": tr.track_id,
                    "species": species,
                    "box": list(p.box),
                    "conf": round(p.conf, 6),
                }
            )

    return {
        "schema": TRACKING_SCHEMA,
        "created_utc": utc_now(),
        "video": seq.video,
        "source": detection_path.name,
        "source_sha256": seq.source_sha256,
        "detection_fingerprint": seq.fingerprint,
        "sample_stride": seq.sample_stride,
        "n_anchors": len(seq.frames),
        "tracker": f"oc_sort({association})",
        "association": association,
        "params": params,
        "n_tracks": len(track_rows),
        "tracks": track_rows,
        "anchors": {f: sorted(rows, key=lambda r: r["track_id"]) for f, rows in sorted(anchors_out.items(), key=lambda kv: int(kv[0]))},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--detections", nargs="+", required=True, help="检测缓存 JSON 路径（可多个）")
    parser.add_argument("--out", type=Path, required=True, help="独立输出目录")
    parser.add_argument("--max-age", type=int, default=DEFAULT_PARAMS["max_age"])
    parser.add_argument("--min-hits", type=int, default=DEFAULT_PARAMS["min_hits"])
    parser.add_argument("--iou-threshold", type=float, default=DEFAULT_PARAMS["iou_threshold"])
    parser.add_argument("--inertia", type=float, default=DEFAULT_PARAMS["inertia"],
                        help="方向代价权重；0 = 关闭 OCM（SORT 对照用）")
    parser.add_argument("--no-use-byte", action="store_true", help="关闭低分二次关联（SORT 对照用）")
    parser.add_argument("--association", choices=("species_split", "single"), default="species_split",
                        help="关联模式；single = 单流 + 物种作元数据（design 4.5 修订）")
    args = parser.parse_args()

    params = dict(DEFAULT_PARAMS)
    params.update(max_age=args.max_age, min_hits=args.min_hits, iou_threshold=args.iou_threshold,
                  inertia=args.inertia)
    if args.no_use_byte:
        params["use_byte"] = False

    args.out.mkdir(parents=True, exist_ok=True)
    entries = []
    for det_path in args.detections:
        det_path = Path(det_path)
        payload = track_video(det_path, params)
        # created_utc 不参与内容指纹：可复现判据比较时剔除
        content = {k: v for k, v in payload.items() if k != "created_utc"}
        out_path = args.out / f"{det_path.stem}.track.json"
        out_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False), encoding="utf-8"
        )
        entries.append(
            {
                "video": payload["video"],
                "detection": det_path.name,
                "detection_sha256": sha256_text(det_path.read_text(encoding="utf-8")),
                "source_sha256": payload["source_sha256"],
                "output": out_path.name,
                "output_content_sha256": sha256_text(json.dumps(content, ensure_ascii=False, sort_keys=True)),
                "n_tracks": payload["n_tracks"],
            }
        )
        print(
            f"[track] {det_path.stem}: {payload['n_tracks']} tracks "
            f"({sum(1 for t in payload['tracks'] if t['species'] == 'cat')} cat / "
            f"{sum(1 for t in payload['tracks'] if t['species'] == 'dog')} dog)"
        )

    manifest = {
        "schema": f"{TRACKING_SCHEMA}-manifest",
        "created_utc": utc_now(),
        "params": params,
        "n_videos": len(entries),
        "entries": entries,
    }
    (args.out / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(f"TRACK DONE -> {args.out}/manifest.json ({len(entries)} videos)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
