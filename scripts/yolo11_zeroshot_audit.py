#!/usr/bin/env python3
"""YOLO11 COCO 预训练 zero-shot 体检 —— t13-1 第一阶段选型证据。

用法（pet 上，conda env yolo）:
    python scripts/yolo11_zeroshot_audit.py \
        --videos-root /home/wyy/mnt/cats \
        --output results/detection/zeroshot_cats

    # 全参数示例
    python scripts/yolo11_zeroshot_audit.py ... \
        --models n,s --conf 0.25 --frame-interval 2 --night-luma 60 \
        --sample-per-group 4 --seed 42 --device 0 --dry-run

输入：
    --videos-root            含 dataset_*/event_*.mp4 的根目录（79 段 cats 视频）

输出（<output>/）：
    report.md / report.json      汇总报告：昼夜双口径（小时/亮度）× 模型 × 类别
    frames/<video>_<model>.json  逐帧原始记录（亮度、各类最高 conf），改口径只需重算报告
    sampled_videos/              昼/夜分层抽样画框视频（类名+conf）
    preannotation/
        yolo/{images,labels,classes.txt}   YOLO 通用格式预标注
        labelstudio/tasks.json             LabelStudio 导入包（含 predictions）
    README.md                    运行参数、阈值、类映射、局限声明

口径：
    检出帧率 = conf>=--conf 的该类框存在帧占比（帧级）
    夜视口径A = 文件名小时 19-23/0-6
    夜视口径B = 帧灰度均值 < --night-luma 或 HSV 饱和度均值 < --night-sat
                （红外夜视帧被补光灯打亮、亮度不低，但几乎无色）
"""
from __future__ import annotations

import argparse
import json
import random
import re
import traceback
from pathlib import Path

import cv2
import numpy as np

# ---- 类目单一事实源（与 management/docs/detection-annotation-taxonomy.md 同步）----
TAXONOMY = [
    "cat", "person", "food_bowl", "water_bowl",
    "litter_box", "toy", "door_window", "cat_face",
    "bowl_unspecified",  # 预标注中间类，仅机器产出
]
TAXONOMY_ID = {name: i for i, name in enumerate(TAXONOMY)}
# COCO 类名 -> 定稿类目（预标注映射；仅这三类进预标注包）
COCO_MAP = {"cat": "cat", "person": "person", "bowl": "bowl_unspecified"}
# 统计口径关心的 COCO 三类
STAT_CLASSES = ["cat", "person", "bowl"]
COCO_ID_TO_NAME = {15: "cat", 0: "person", 45: "bowl"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="YOLO11 COCO zero-shot audit for cats videos")
    p.add_argument("--videos-root", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--models", default="n,s", help="YOLO11 档位逗号分隔（默认 n,s）")
    p.add_argument("--conf", type=float, default=0.25, help="检出判定阈值（默认 0.25）")
    p.add_argument("--frame-interval", type=float, default=2.0, help="预标注抽帧间隔秒（默认 2）")
    p.add_argument("--night-luma", type=float, default=60.0, help="夜视帧灰度均值阈值（默认 60）")
    p.add_argument("--night-sat", type=float, default=20.0,
                   help="夜视帧饱和度阈值（默认 20；红外帧亮而无色，饱和度低）")
    p.add_argument("--sample-per-group", type=int, default=4, help="昼/夜各组抽样视频数")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--device", default="0", help="cuda 设备号或 cpu")
    p.add_argument("--imgsz", type=int, default=640,
                   help="推理输入分辨率（默认 640；2880×1620 源建议 1280 提升小目标）")
    p.add_argument("--preanno-model", default="s", help="预标注与抽样视频用哪个档位（默认 s）")
    p.add_argument("--night-hours", default="19-23,0-6", help="夜视口径A的小时范围")
    p.add_argument("--dry-run", action="store_true", help="只处理前 2 段各 200 帧，不写重产物")
    return p.parse_args()


def parse_night_hours(spec: str) -> set[int]:
    hours: set[int] = set()
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            hours.update(range(int(a), int(b) + 1))
        else:
            hours.add(int(part))
    return hours


def find_videos(root: Path) -> list[Path]:
    vids: list[Path] = []
    for sub in sorted(root.iterdir()):
        if sub.is_dir() and sub.name.startswith("dataset_"):
            vids.extend(sorted(sub.glob("event_*.mp4")))
    return vids


def video_hour(path: Path) -> int | None:
    m = re.match(r"event_\d{8}_(\d{2})", path.name)
    return int(m.group(1)) if m else None


def frame_luma_sat(img: np.ndarray) -> tuple[float, float]:
    """下采样灰度均值 + HSV 饱和度均值（行/列各取 1/4）。

    红外夜视帧被补光灯打亮，亮度不低但几乎无色（饱和度低），
    因此夜视判据 = 亮度低 OR 饱和度低。
    """
    small = img[::4, ::4]
    luma = float(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).mean())
    sat = float(cv2.cvtColor(small, cv2.COLOR_BGR2HSV)[:, :, 1].mean())
    return luma, sat


def stats_from_result(res, conf_thres: float) -> dict[str, float]:
    """三类统计：{coco_name: 该类最高 conf（无检出为 0.0）}。"""
    out = {c: 0.0 for c in STAT_CLASSES}
    if res.boxes is None or len(res.boxes) == 0:
        return out
    for c, cf in zip(res.boxes.cls.tolist(), res.boxes.conf.tolist()):
        name = COCO_ID_TO_NAME.get(int(c))
        if name is not None and cf >= conf_thres:
            out[name] = max(out[name], float(cf))
    return out


def open_writer(path: Path, fps: float, w: int, h: int) -> cv2.VideoWriter:
    """优先 avc1（H.264），不可用回退 mp4v。"""
    for codec in ("avc1", "mp4v"):
        vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec), fps, (w, h))
        if vw.isOpened():
            return vw
        vw.release()
    raise RuntimeError(f"VideoWriter 无法打开: {path}")


def audit_pass(model, video: Path, out_dir: Path, args, model_tag: str,
               night_hours: set[int], preanno: dict | None) -> dict:
    """单视频单模型：stream 逐帧统计 + 可选预标注导出。返回 per-video 汇总。

    preanno 非 None 时导出预标注（YOLO txt + 图像 + LabelStudio task）。
    """
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    preanno_step = max(1, round(fps * args.frame_interval))
    max_frames = 200 if args.dry_run else 10**9

    frames_rec: list[dict] = []
    hour = video_hour(video)
    for idx, res in enumerate(
        model.predict(source=str(video), stream=True, verbose=False,
                      conf=args.conf, device=args.device, imgsz=args.imgsz)
    ):
        if idx >= max_frames:
            break
        luma, sat = frame_luma_sat(res.orig_img)
        stats = stats_from_result(res, args.conf)
        frames_rec.append({"f": idx, "luma": round(luma, 1), "sat": round(sat, 1),
                           **{c: round(v, 3) for c, v in stats.items()}})
        if preanno is not None and idx % preanno_step == 0:
            export_preannotation(res, idx, preanno, args)

    if not args.dry_run:
        with open(out_dir / f"{video.stem}_yolo11{model_tag}.json", "w") as f:
            json.dump({"video": video.name, "model": model_tag, "hour": hour,
                       "fps": round(fps, 2), "n_frames": len(frames_rec),
                       "frames": frames_rec}, f)

    def is_night(r: dict) -> bool:
        # IR 帧亮而无色：亮度低 OR 饱和度低
        return r["luma"] < args.night_luma or r["sat"] < args.night_sat

    n = len(frames_rec)
    day = [r for r in frames_rec if not is_night(r)]
    night = [r for r in frames_rec if is_night(r)]
    summary: dict = {"video": video.name, "model": model_tag, "hour": hour,
                     "n_frames": n, "fps": round(fps, 2),
                     "night_ratio_B": len(night) / max(1, n),
                     "group": "night_a" if (hour is not None and hour in night_hours) else "day_a"}
    for c in STAT_CLASSES:
        summary[f"{c}_all"] = sum(1 for r in frames_rec if r[c] > 0) / max(1, n)
        summary[f"{c}_dayB"] = sum(1 for r in day if r[c] > 0) / max(1, len(day))
        summary[f"{c}_nightB"] = sum(1 for r in night if r[c] > 0) / max(1, len(night))
        detected = [r[c] for r in frames_rec if r[c] > 0]
        summary[f"{c}_conf"] = float(np.mean(detected)) if detected else 0.0
    return summary


def export_preannotation(res, idx: int, preanno: dict, args) -> None:
    stem = f"{preanno['video_stem']}_f{idx:06d}"
    frame = res.orig_img
    H, W = frame.shape[:2]
    cv2.imwrite(str(preanno["img_dir"] / f"{stem}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])

    lines, shapes = [], []
    if res.boxes is not None and len(res.boxes) > 0:
        for (x1, y1, x2, y2), c, cf in zip(
            res.boxes.xyxy.tolist(), res.boxes.cls.tolist(), res.boxes.conf.tolist()
        ):
            name = COCO_ID_TO_NAME.get(int(c))
            if name is None or cf < args.conf:
                continue
            target = COCO_MAP[name]
            lines.append(f"{TAXONOMY_ID[target]} {(x1+x2)/2/W:.6f} {(y1+y2)/2/H:.6f} "
                         f"{(x2-x1)/W:.6f} {(y2-y1)/H:.6f}")
            shapes.append({
                "from_name": "label", "to_name": "image",
                "type": "rectanglelabels", "original_width": W, "original_height": H,
                "image_rotation": 0,
                "value": {"rotation": 0, "x": 100 * x1 / W, "y": 100 * y1 / H,
                          "width": 100 * (x2 - x1) / W, "height": 100 * (y2 - y1) / H,
                          "rectanglelabels": [target]},
            })
    (preanno["lbl_dir"] / f"{stem}.txt").write_text("\n".join(lines))
    preanno["ls_tasks"].append({
        "data": {"image": f"images/{stem}.jpg"},
        "predictions": [{"model_version": f"yolo11{args.preanno_model}-coco-zeroshot",
                         "score": 0.0, "result": shapes}],
    })


def render_sampled(model, video: Path, out_path: Path, args) -> None:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    vw = open_writer(out_path, fps, w, h)
    max_frames = 200 if args.dry_run else 10**9
    for idx, res in enumerate(
        model.predict(source=str(video), stream=True, verbose=False,
                      conf=args.conf, device=args.device, imgsz=args.imgsz)
    ):
        if idx >= max_frames:
            break
        frame = res.orig_img
        if res.boxes is not None and len(res.boxes) > 0:
            for (x1, y1, x2, y2), c, cf in zip(
                res.boxes.xyxy.tolist(), res.boxes.cls.tolist(), res.boxes.conf.tolist()
            ):
                name = COCO_ID_TO_NAME.get(int(c))
                if name is None or cf < args.conf:
                    continue
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                cv2.putText(frame, f"{name} {cf:.2f}", (int(x1), max(15, int(y1) - 6)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        vw.write(frame)
    vw.release()


def build_report(summaries: list[dict], failures: list[dict], args, models: list[str]) -> tuple[str, dict]:
    def rate(rows, key):
        return float(np.mean([r[key] for r in rows])) if rows else 0.0

    def weightedB(rows, c, which):
        num = den = 0.0
        for r in rows:
            den += r["n_frames"]
            num += r[f"{c}_{which}"] * r["n_frames"]
        return num / den if den else 0.0

    rep: dict = {
        "params": vars(args).copy(),
        "failures": failures,
        "limitation": "79 段视频全部来自 2026-08-06 单机位单日，结论仅代表该域表现",
        "per_video": summaries,
        "models": {},
    }
    lines = [
        "# YOLO11 COCO zero-shot 体检报告（cats 79 段）", "",
        f"- 模型档位：{', '.join('yolo11' + m for m in models)}"
        f"（conf≥{args.conf}，imgsz={args.imgsz}，device={args.device}）",
        f"- 夜视口径A（小时 {args.night_hours}）与口径B（帧亮度 <{args.night_luma} 或饱和度 "
        f"<{args.night_sat}，红外帧亮而无色）并存；逐帧原始数据在 frames/，改口径只需重算",
        f"- 失败视频：{len(failures)} 段" + (f" — {failures}" if failures else ""),
        f"- **局限**：{rep['limitation']}", "",
    ]
    for m in models:
        rows = [s for s in summaries if s.get("model") == m and "error" not in s]
        night_a = [s for s in rows if s["group"] == "night_a"]
        day_a = [s for s in rows if s["group"] == "day_a"]
        lines += [f"## yolo11{m}", "",
                  "| 类别 | 全量检出帧率 | 口径A白天 | 口径A夜视 | 口径B白天 | 口径B夜视 | 均值conf |",
                  "|---|---|---|---|---|---|---|"]
        rep["models"][m] = {}
        for c in STAT_CLASSES:
            conf_mean = rate(rows, f"{c}_conf")
            lines.append("| " + " | ".join([
                c,
                f"{rate(rows, c + '_all'):.1%}",
                f"{rate(day_a, c + '_all'):.1%}",
                f"{rate(night_a, c + '_all'):.1%}",
                f"{weightedB(rows, c, 'dayB'):.1%}",
                f"{weightedB(rows, c, 'nightB'):.1%}",
                f"{conf_mean:.2f}",
            ]) + " |")
            nightB = weightedB(rows, c, "nightB")
            rep["models"][m][c] = {
                "all": rate(rows, c + "_all"),
                "dayA": rate(day_a, c + "_all"), "nightA": rate(night_a, c + "_all"),
                "dayB": weightedB(rows, c, "dayB"), "nightB": nightB,
                "night_miss_B": 1 - nightB, "conf": conf_mean,
            }
        lines.append("")
    lines += ["## 夜视漏检率（口径B，cat 类）", ""]
    for m in models:
        v = rep["models"][m]["cat"]["night_miss_B"]
        lines.append(f"- yolo11{m}: **{v:.1%}**")
    lines.append("")
    return "\n".join(lines), rep


def write_readme(out: Path, args, models: list[str]) -> None:
    (out / "README.md").write_text(f"""# YOLO11 zero-shot 体检产物

- 运行参数：{json.dumps(vars(args), ensure_ascii=False)}
- 模型：{', '.join('yolo11' + m for m in models)}（COCO 预训练，未微调，imgsz={args.imgsz}）
- 统计口径：帧级，conf≥{args.conf}；夜视双口径（小时 {args.night_hours} /
  帧亮度 <{args.night_luma} 或饱和度 <{args.night_sat}——红外帧亮而无色）
- 预标注：yolo11{args.preanno_model} 产出，每 {args.frame_interval}s 一帧；
  COCO cat→cat、person→person、bowl→bowl_unspecified（中间类，人工细分）
- 类目全集（classes.txt，单一事实源）：{', '.join(TAXONOMY)}
- 类目定义：仓库 docs/detection-annotation-taxonomy.md（v0.1）
- 数据事实：79 段全部 2026-08-06 单机位单日、2880×1620、HEVC、无音轨、
  全部可解码（33109 帧 / 36.9 min）
- **局限**：结论仅代表该域（单日单机位）表现，多场景泛化待 t13-1 标注后评测
- LabelStudio 导入：preannotation/labelstudio/tasks.json
  （配 local storage，task 中 image 为 images/ 相对路径）
""")


def main() -> None:
    args = parse_args()
    night_hours = parse_night_hours(args.night_hours)
    random.seed(args.seed)

    root, out = Path(args.videos_root), Path(args.output)
    (out / "frames").mkdir(parents=True, exist_ok=True)
    (out / "sampled_videos").mkdir(parents=True, exist_ok=True)
    (out / "preannotation" / "yolo" / "images").mkdir(parents=True, exist_ok=True)
    (out / "preannotation" / "yolo" / "labels").mkdir(parents=True, exist_ok=True)
    (out / "preannotation" / "labelstudio").mkdir(parents=True, exist_ok=True)

    videos = find_videos(root)
    if args.dry_run:
        videos = videos[:2]
    print(f"videos: {len(videos)}  output: {out}  device: {args.device}")

    from ultralytics import YOLO
    models = args.models.split(",")
    summaries, failures, ls_tasks = [], [], []

    for m in models:
        model = YOLO(f"yolo11{m}.pt")
        for i, v in enumerate(videos):
            want_preanno = (m == args.preanno_model) and not args.dry_run
            preanno = None
            if want_preanno:
                preanno = {
                    "video_stem": v.stem,
                    "img_dir": out / "preannotation" / "yolo" / "images",
                    "lbl_dir": out / "preannotation" / "yolo" / "labels",
                    "ls_tasks": ls_tasks,
                }
            try:
                summaries.append(audit_pass(model, v, out / "frames", args, m,
                                             night_hours, preanno))
            except Exception as e:  # noqa: BLE001 失败隔离：单视频不中断整批
                failures.append({"video": v.name, "model": m,
                                 "error": f"{type(e).__name__}: {e}"})
                traceback.print_exc()
            print(f"[yolo11{m}] {i + 1}/{len(videos)} {v.name} "
                  f"{'ERR' if failures and failures[-1]['video'] == v.name else 'ok'}")

    if not args.dry_run:
        (out / "preannotation" / "yolo" / "classes.txt").write_text("\n".join(TAXONOMY) + "\n")
        with open(out / "preannotation" / "labelstudio" / "tasks.json", "w") as f:
            json.dump(ls_tasks, f, ensure_ascii=False)

    # 抽样渲染：昼/夜分层（按口径B夜帧占比 >0.5 分组），各组 sample-per-group 段
    ok_rows = [s for s in summaries if "error" not in s]
    seen: set[str] = set()
    night_vids, day_vids = [], []
    for s in ok_rows:
        if s["video"] in seen:
            continue
        seen.add(s["video"])
        (night_vids if s["night_ratio_B"] > 0.5 else day_vids).append(s["video"])
    rng = random.Random(args.seed)
    samp_n = rng.sample(night_vids, min(args.sample_per_group, len(night_vids)))
    samp_d = rng.sample(day_vids, min(args.sample_per_group, len(day_vids)))
    vmap = {v.name: v for v in videos}
    render_model = YOLO(f"yolo11{args.preanno_model}.pt")
    for tag, group in [("night", samp_n), ("day", samp_d)]:
        for name in group:
            v = vmap.get(name)
            if v is None:
                continue
            try:
                render_sampled(render_model, v, out / "sampled_videos" / f"{tag}_{name}", args)
                print(f"rendered {tag}_{name}")
            except Exception as e:  # noqa: BLE001
                print(f"render failed {name}: {e}")

    report_md, report_json = build_report(summaries, failures, args, models)
    (out / "report.md").write_text(report_md)
    with open(out / "report.json", "w") as f:
        json.dump(report_json, f, ensure_ascii=False, indent=1)
    if not args.dry_run:
        write_readme(out, args, models)
    print("\n" + report_md)


if __name__ == "__main__":
    main()
