"""亮点抓取特征提取：单视频 → `pet.highlight.v1` 载荷 JSON（可选写入本地 outbox）。

提取画面亮度、对比度、宠物活动幅度、宠物身体面积占比与时长、面部暴露面积占比与时长，
并附行为识别时间轴，供上报云端判断。本脚本不做网络上传。

示例（需 CUDA GPU，v1 七类 X3D-S + YOLO11n-seg + Haar 猫脸）：
  python scripts/extract_highlight_features.py --video datasets/cat_raw/videos/x.mp4 \
      --pet-source yolo_seg --yolo-weights checkpoints/ultralytics/yolo11n-seg.pt \
      --action-config configs/cat_action_x3d_s_v1.py \
      --action-checkpoint results/training/cat_action_v1/x3d_s/work/best_macro_f1_epoch_20.pth \
      --out results/highlights/x.json --outbox results/highlights/outbox

无模型依赖（只算画面指标）：
  python scripts/extract_highlight_features.py --video x.mp4 --pet-source none --face none --out x.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from petlib.highlights.actions import load_timeline  # noqa: E402
from petlib.highlights.aggregate import HighlightConfig  # noqa: E402
from petlib.highlights.report import extract_highlights, write_outbox  # noqa: E402
from petlib.highlights.sources import build_face_source, build_pet_source  # noqa: E402


def parse_args(argv=None) -> argparse.Namespace:
    d = HighlightConfig()
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True, help="载荷 JSON 输出路径")
    ap.add_argument("--outbox", help="本地 outbox 目录（断网缓存，<event_id>.json，不覆盖）")
    ap.add_argument("--device-id")
    ap.add_argument("--camera-id")
    ap.add_argument("--start-time", help="片段起始时间（ISO 8601），透传到载荷")
    ap.add_argument("--include-samples", action="store_true", help="附逐采样点明细（体积较大）")

    g = ap.add_argument_group("宠物 / 面部来源")
    g.add_argument("--pet-source", choices=["yolo_seg", "track_json", "none"], default="yolo_seg")
    g.add_argument("--yolo-weights", default=str(REPO / "checkpoints" / "ultralytics" / "yolo11n-seg.pt"),
                   help="本地权重路径（不会自动下载）")
    g.add_argument("--yolo-conf", type=float, default=0.25)
    g.add_argument("--track-json", help="pet_detect_track.py 输出的 track.json")
    g.add_argument("--face", choices=["haar", "none"], default="haar")
    g.add_argument("--face-cascade", help="haarcascade_frontalcatface_extended.xml 路径（默认自动查找）")
    g.add_argument("--device", default=None, help="cuda:0 / cpu（YOLO 与行为模型共用）")

    g = ap.add_argument_group("行为识别")
    g.add_argument("--actions-json", help="已有时间轴 JSON/JSONL（t_start/t_end/label/score）")
    g.add_argument("--action-config", help="MMAction2 配置（如 configs/cat_action_x3d_s_v1.py）")
    g.add_argument("--action-checkpoint")
    g.add_argument("--action-window", type=float, default=4.0)
    g.add_argument("--action-stride", type=float, default=2.0)
    g.add_argument("--review-score", type=float, default=0.5, help="低于此分数的行为段标记云端复核")

    g = ap.add_argument_group("分析参数")
    g.add_argument("--analysis-fps", type=float, default=d.analysis_fps)
    g.add_argument("--analysis-width", type=int, default=d.analysis_width)
    g.add_argument("--window-sec", type=float, default=d.window_sec)
    g.add_argument("--body-large-ratio", type=float, default=d.body_large_ratio)
    g.add_argument("--activity-thresholds", type=float, nargs=3, default=list(d.activity_thresholds),
                   metavar=("STATIC", "LOW", "MEDIUM"))
    g.add_argument("--gap-fill-sec", type=float, default=d.gap_fill_sec)
    g.add_argument("--min-segment-sec", type=float, default=d.min_segment_sec)
    args = ap.parse_args(argv)
    if args.pet_source == "track_json" and not args.track_json:
        ap.error("--pet-source track_json requires --track-json")
    if bool(args.action_config) != bool(args.action_checkpoint):
        ap.error("--action-config and --action-checkpoint must be given together")
    if args.action_config and args.actions_json:
        ap.error("use either --actions-json or --action-config, not both")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    cfg = HighlightConfig(
        analysis_fps=args.analysis_fps, analysis_width=args.analysis_width, window_sec=args.window_sec,
        body_large_ratio=args.body_large_ratio, activity_thresholds=tuple(args.activity_thresholds),
        gap_fill_sec=args.gap_fill_sec, min_segment_sec=args.min_segment_sec)
    pet_source = build_pet_source(args.pet_source, weights=args.yolo_weights, conf=args.yolo_conf,
                                  track_json=args.track_json, device=args.device)
    face_source = build_face_source(args.face, cascade_path=args.face_cascade)

    behavior = behavior_source = recognizer = None
    if args.actions_json:
        behavior = load_timeline(args.actions_json)
        behavior_source = {"source": "timeline_json", "file": Path(args.actions_json).name}
    elif args.action_config:
        from petlib.highlights.actions import MMActionWindowRecognizer

        recognizer = MMActionWindowRecognizer(args.action_config, args.action_checkpoint,
                                              device=args.device or "cuda:0",
                                              window_sec=args.action_window, stride_sec=args.action_stride)

    payload = extract_highlights(args.video, pet_source, face_source, cfg, behavior=behavior,
                                 behavior_source=behavior_source, recognizer=recognizer,
                                 review_score=args.review_score, device_id=args.device_id,
                                 camera_id=args.camera_id, start_time=args.start_time,
                                 include_samples=args.include_samples)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    s = payload["summary"]
    print(f"HIGHLIGHT DONE -> {out} | event={payload['event_id']} dur={s['duration_sec']}s "
          f"visible={s['pet_visible_sec']}s face={s['face_exposed_sec']}s "
          f"behavior_segments={len(payload['behavior']['segments'])}", flush=True)
    if args.outbox:
        path, new = write_outbox(payload, args.outbox)
        print(f"OUTBOX {'WRITTEN' if new else 'EXISTS'} -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
