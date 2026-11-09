#!/usr/bin/env python3
"""轨迹质量三指标统计（multi-pet-sort-tracking 2.2）。

design 4.2 的指标在无 GT 条件下的可核对代理：
- 轨迹碎片数/个体：把同一物种的 confirmed 轨迹按时间近邻聚合为"个体"，
  个体数 = 聚类数；碎片 = 该个体的轨迹段数 - 1。
- 轨迹数与个体数一致性：每个多宠物锚点上"活跃轨迹数" vs 检测缓存里
  该锚点的 pet_count，统计不一致锚点占比（一致性比率）。
- 身份交换：无 GT 不能直接数；代理指标 = 轨迹重叠度（同一物种两条轨迹
  在相邻锚点间 IoU > 0.5 的次数，交叉/交换的必要非充分信号），
  人工核对（2.4）才是交换次数的判定来源。

输出 metrics.json：逐视频明细 + 汇总。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.tracking.anchors import load_anchor_sequence  # noqa: E402


def box_iou(a, b) -> float:
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)


def load_tracks(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["tracks"]


def cluster_individuals(tracks: list[dict], same_species_gap: int = 24) -> list[list[dict]]:
    """同物种轨迹按时间近邻聚合：轨迹 A 结束后 gap 个锚点内出现下一条 B 视为同一个体。

    gap=24 锚点 ≈ 8s（stride=5 @15fps），取 max_age=8 的 3 倍，
    允许一条轨迹因漏检断裂后由下一条接续。
    """
    clusters: list[list[dict]] = []
    by_species: dict[str, list[dict]] = {}
    for t in tracks:
        if t["state"] != "confirmed":
            continue
        by_species.setdefault(t["species"], []).append(t)
    for species in sorted(by_species):
        seq = sorted(by_species[species], key=lambda t: t["first_frame"])
        current: list[dict] = []
        for t in seq:
            if current and t["first_frame"] - current[-1]["last_frame"] > same_species_gap * 5:
                clusters.append(current)
                current = []
            current.append(t)
        if current:
            clusters.append(current)
    return clusters


def overlap_swaps(tracks: list[dict], iou_thr: float = 0.5) -> int:
    """同一物种两条 confirmed 轨迹在重叠帧上 IoU > iou_thr 的次数（交换代理信号）。"""
    by_species: dict[str, list[dict]] = {}
    for t in tracks:
        if t["state"] != "confirmed":
            continue
        by_species.setdefault(t["species"], []).append(t)
    n = 0
    for seq in by_species.values():
        for i in range(len(seq)):
            for j in range(i + 1, len(seq)):
                fa = {p["frame"]: p["box"] for p in seq[i]["points"]}
                fb = {p["frame"]: p["box"] for p in seq[j]["points"]}
                for f in set(fa) & set(fb):
                    if box_iou(fa[f], fb[f]) > iou_thr:
                        n += 1
    return n


def anchor_consistency(track_payload: dict, pet_counts: dict[str, int]) -> dict:
    """每个锚点：活跃 confirmed 轨迹数 vs 该锚点的宠物数。

    pet_counts 必须来自跟踪器实际看到的输入流（含 design 4.11 的 IoS 去重），
    否则去重后轨迹数减少、分母却仍按原缓存计，一致性会被系统性低估。
    """
    anchors_track = track_payload["anchors"]
    anchors_det = pet_counts
    n_total = n_multi = n_match = 0
    for frame, rows in anchors_track.items():
        pet_count = anchors_det.get(frame)
        if pet_count is None:
            continue
        n_total += 1
        if pet_count >= 2:
            n_multi += 1
            if len(rows) == pet_count:
                n_match += 1
    return {
        "anchors_compared": n_total,
        "multi_pet_anchors": n_multi,
        "multi_pet_matched": n_match,
        "consistency": round(n_match / n_multi, 4) if n_multi else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracks-dir", type=Path, required=True)
    parser.add_argument("--detections-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-dedup", action="store_true",
                        help="按未去重的原始候选计较对齐（对照臂用）")
    args = parser.parse_args()

    per_video = []
    for track_path in sorted(args.tracks_dir.glob("*.track.json")):
        payload = json.loads(track_path.read_text(encoding="utf-8"))
        det_path = args.detections_dir / f"{track_path.name.removesuffix('.track.json')}.json"
        seq = load_anchor_sequence(det_path, apply_dedup=not args.no_dedup)
        pet_counts = {str(f): len(dets) for f, dets in zip(seq.frames, seq.detections, strict=True)}
        tracks = payload["tracks"]
        clusters = cluster_individuals(tracks)
        cons = anchor_consistency(payload, pet_counts)
        per_video.append(
            {
                "video": payload["video"],
                "n_tracks_total": len(tracks),
                "n_tracks_confirmed": sum(1 for t in tracks if t["state"] == "confirmed"),
                "n_individuals_estimated": len(clusters),
                "fragments_per_individual": [len(c) - 1 for c in clusters],
                "total_fragments": sum(len(c) - 1 for c in clusters),
                "overlap_swap_signals": overlap_swaps(tracks),
                "anchor_consistency": cons,
            }
        )

    summary = {
        "videos": len(per_video),
        "fragments_per_individual_max": max(
            (v["fragments_per_individual"] or [0]) and max(v["fragments_per_individual"]) or 0
            for v in per_video
        ),
        "overlap_swap_signals_total": sum(v["overlap_swap_signals"] for v in per_video),
        "anchor_consistency_min": min(
            (v["anchor_consistency"]["consistency"] or 1.0) for v in per_video
        ),
        "anchor_consistency_median": sorted(
            v["anchor_consistency"]["consistency"] or 1.0 for v in per_video
        )[len(per_video) // 2],
    }
    report = {
        "schema": "multi-pet-tracking-metrics-v1",
        "metrics_definition": {
            "fragment": "same-species confirmed tracks clustered by temporal adjacency (gap<=24 anchors); fragments = cluster size - 1",
            "swap_signal": "same-species confirmed track pairs with IoU>0.5 on shared frames (proxy; ground-truth swaps judged by human review)",
            "anchor_consistency": "multi-pet anchors where #active tracks == pet_count / #multi-pet anchors",
        },
        "summary": summary,
        "per_video": per_video,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    print(f"METRICS -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
