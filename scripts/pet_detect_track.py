"""猫居中预处理：多 prompt 抽样检测 + 插值平滑 + 逐帧运动校正 → 轨迹 JSON。

batch-followcam-extraction 任务 1.1（design B1/B2/B3）。

流程：
  1. GroundingDINO 多 prompt 抽样检测（每 sample_stride 帧，一次前向返回全部类别）
  2. 猫主轨迹关联（最高置信框，单猫场景）→ 线性插值到全帧 → 滑动平均平滑
  3. 逐帧运动校正（design B2）：背景模型（时序中值）前景 mask 的连通域
     与插值框相交 → 框向外扩展覆盖（校正幅度设上限防漂移）；无前景则不动
  4. 空间状态层：猫框底边中点落入家具框 → "cat on X"（≥hold_sec 迟滞）
  5. 产物（design B3 契约）：轨迹 JSON（猫框含 interpolated/motion_corrected
     标记 + 家具框 + 空间状态序列）

用法（pet plf 环境；GPU 任务前须 nvidia-smi 查占用）：
  CUDA_VISIBLE_DEVICES=0 python scripts/plf_detect_track.py \
      --video <mp4> --out results/batch/<段名> [--sample-stride 10]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import cv2
import numpy as np
import torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MODEL_ID = "IDEA-Research/grounding-dino-tiny"
PROMPT = "cat. bed. table. sofa. shelf."
CAT = "cat"
FURNITURE = ["bed", "table", "sofa", "shelf"]
SMOOTH_WIN = 5
MAX_CORRECT_RATIO = 0.25  # 单帧校正幅度上限（相对框边长的比例），防漂移


def _iou(a, b) -> float:
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / max(1e-6, ua)


def _dedup_furniture(items: list) -> list:
    """同类家具框按置信度去重（IoU>0.5 保留最高），防同帧多框重复计数。"""
    out = []
    for lab, b, s in sorted(items, key=lambda x: -x[2]):
        if all(_iou(b, b2) < 0.5 for l2, b2, _ in out if l2 == lab):
            out.append((lab, b, s))
    return out


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sample-stride", type=int, default=10)
    ap.add_argument("--threshold", type=float, default=0.3)
    ap.add_argument("--prompt", default=PROMPT)
    ap.add_argument("--hold-sec", type=float, default=1.5, help="空间状态迟滞秒数")
    ap.add_argument("--bg-lr", type=float, default=0.002,
                    help="背景模型学习率（慢更新，避免静止猫被快速吸收）")
    ap.add_argument("--off-alpha", type=float, default=0.6,
                    help="偏移场 EMA 系数（v4 相机路径）")
    ap.add_argument("--off-max-v", type=float, default=0.05,
                    help="偏移限速（帧宽比例/帧，平移通道）")
    ap.add_argument("--off-alpha-size", type=float, default=0.15,
                    help="尺寸偏移 EMA（慢于平移，压变焦呼吸）")
    ap.add_argument("--off-max-v-size", type=float, default=0.02,
                    help="尺寸偏移限速（帧宽比例/帧）")
    ap.add_argument("--no-motion-correct", action="store_true",
                    help="关闭逐帧运动校正（消融对照用，任务 1.2）")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    os.makedirs(args.out, exist_ok=True)
    from transformers import AutoProcessor, GroundingDinoForObjectDetection

    device = "cuda:0"
    processor = AutoProcessor.from_pretrained(MODEL_ID)
    model = GroundingDinoForObjectDetection.from_pretrained(MODEL_ID).to(device).eval()

    cap = cv2.VideoCapture(args.video)
    if not cap.isOpened():
        print(f"ERROR: cannot open video {args.video}", flush=True)
        sys.exit(2)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames: list[np.ndarray] = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        frames.append(f)
    cap.release()
    T = len(frames)
    if T == 0:
        print(f"ERROR: zero frames read from {args.video}", flush=True)
        sys.exit(2)
    H, W = frames[0].shape[:2]
    print(f"video: {T} frames {W}x{H} @{fps:.1f}fps", flush=True)

    # ── 1. 抽样检测（多 prompt 一次前向）─────────────────────────────
    sampled: dict[int, dict] = {}  # frame -> {"cat": (box, conf), "furniture": {...}}
    with torch.no_grad():
        for f in range(0, T, args.sample_stride):
            rgb = cv2.cvtColor(frames[f], cv2.COLOR_BGR2RGB)
            inputs = processor(images=rgb, text=args.prompt, return_tensors="pt").to(device)
            out = model(**inputs)
            res = processor.post_process_grounded_object_detection(
                out, inputs.input_ids, box_threshold=args.threshold,
                text_threshold=args.threshold, target_sizes=[(H, W)])[0]
            boxes = res["boxes"].cpu().numpy()
            scores = res["scores"].cpu().numpy()
            labels = res["labels"]
            entry: dict = {"cat": None, "furniture": []}
            for box, sc, lab in zip(boxes, scores, labels):
                if lab == CAT:
                    if entry["cat"] is None or sc > entry["cat"][1]:
                        entry["cat"] = (box, float(sc))
                elif lab in FURNITURE:
                    entry["furniture"].append((lab, box, float(sc)))
            entry["furniture"] = _dedup_furniture(entry["furniture"])
            if entry["cat"] is not None:
                sampled[f] = entry
    n_sampled = len(sampled)
    print(f"sampled frames with cat: {n_sampled}/{len(range(0, T, args.sample_stride))}",
          flush=True)

    # ── 2. 插值 + 平滑 ──────────────────────────────────────────────
    fs = sorted(sampled)
    known_f = np.array(fs)
    known_b = np.array([sampled[f]["cat"][0] for f in fs])
    all_boxes = np.zeros((T, 4), dtype=np.float32)
    for c in range(4):
        all_boxes[:, c] = np.interp(np.arange(T), known_f, known_b[:, c])
    kernel = np.ones(SMOOTH_WIN) / SMOOTH_WIN
    smooth = np.vstack(
        [np.convolve(all_boxes[:, c], kernel, mode="same") for c in range(4)]).T
    interpolated = np.ones(T, dtype=bool)
    interpolated[fs] = False

    # 家具框：最近抽样帧的家具（稀疏落盘，不插值）
    furn_at = {}
    for f in fs:
        furn_at[f] = [(lab, b.tolist(), sc) for lab, b, sc in sampled[f]["furniture"]]

    # ── 3. 逐帧运动校正 v2（design B2：覆盖度门槛 + 只扩不缩）───────────
    bg = cv2.createBackgroundSubtractorMOG2(history=120, varThreshold=25,
                                            detectShadows=False)
    WARMUP = 15
    MIN_COVER_RATIO = 0.2  # 前景对框覆盖度门槛（0.35 会拦住快速移动时的合法校正）
    corrected = np.zeros(T, dtype=bool)
    track = []
    prev_hit = False  # 时序一致性门控：需连续两帧前景命中（滤单帧红外噪声）
    for i in range(T):
        box = smooth[i].copy()
        is_sampled = (i % args.sample_stride == 0)
        hit_now = False
        if not args.no_motion_correct and not is_sampled and i >= WARMUP:
            fg = bg.apply(frames[i], learningRate=args.bg_lr)
            fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN,
                                  np.ones((5, 5), np.uint8))
            cnts, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)
            x1, y1, x2, y2 = box
            bw, bh = x2 - x1, y2 - y1
            # 取与框相交面积最大的连通域
            best = None
            best_inter = 0.0
            for c in cnts:
                cbx, cby, cbw, cbh = cv2.boundingRect(c)
                ix = max(x1, cbx); iy = max(y1, cby)
                ix2 = min(x2, cbx + cbw); iy2 = min(y2, cby + cbh)
                inter = max(0, ix2 - ix) * max(0, iy2 - iy)
                if inter > best_inter:
                    best_inter = inter
                    best = (cbx, cby, cbw, cbh)
            if best is not None and best_inter > 0:
                cover = best_inter / max(1.0, bw * bh)
                hit_now = cover >= MIN_COVER_RATIO
                if hit_now and prev_hit:
                    bx, by, bw2, bh2 = best
                    # 只扩不缩：并集，四边永不内收（防 v1 静止猫切切切）
                    ux1, uy1 = min(x1, bx), min(y1, by)
                    ux2, uy2 = max(x2, bx + bw2), max(y2, by + bh2)
                    # 单帧外扩幅度上限（相对原框边长）
                    ux1 = max(ux1, x1 - MAX_CORRECT_RATIO * bw)
                    uy1 = max(uy1, y1 - MAX_CORRECT_RATIO * bh)
                    ux2 = min(ux2, x2 + MAX_CORRECT_RATIO * bw)
                    uy2 = min(uy2, y2 + MAX_CORRECT_RATIO * bh)
                    new = np.array([ux1, uy1, ux2, uy2], dtype=np.float32)
                    if not np.allclose(new, box, atol=0.5):
                        corrected[i] = True
                        box = new
        prev_hit = hit_now
        track.append({
            "frame": i,
            "box": [round(float(v), 1) for v in box],
            "interpolated": bool(interpolated[i]),
            "motion_corrected": bool(corrected[i]),
        })

    # ── 3b. 相机路径 v4（design B2：精确过锚点 + 校正作为锚点间平滑偏移）──────
    # 抽样帧 camera_box ≡ interp-only（硬性要求）；校正量以半余弦窗约束在间隙内
    # 平滑生效/退出，EMA 状态在锚点处强制归零。
    sampled_mask = np.zeros(T, dtype=bool)
    sampled_mask[::args.sample_stride] = True
    idx = np.arange(T)
    prev_anchor = (idx // args.sample_stride) * args.sample_stride
    next_anchor = np.minimum(prev_anchor + args.sample_stride,
                             ((T - 1) // args.sample_stride) * args.sample_stride)
    dmin = np.minimum(idx - prev_anchor, next_anchor - idx)
    half = args.sample_stride / 2
    w = np.where(sampled_mask, 0.0, 0.5 * (1 - np.cos(np.pi * dmin / half)))

    raw_off = np.zeros((T, 4), dtype=np.float64)
    for rec in track:
        i = rec["frame"]
        raw_off[i] = np.array(rec["box"]) - smooth[i]  # 非校正帧为 0

    # v6：偏移场拆平移(x1,y1)/缩放(x2,y2 视为 w,h 增量)双通道——缩放重阻尼压变焦呼吸
    max_vc = args.off_max_v * W
    max_vs = args.off_max_v_size * W
    off = np.zeros((T, 4), dtype=np.float64)
    curv = np.zeros(4)
    for i in range(T):
        if sampled_mask[i]:
            curv = np.zeros(4)  # 锚点处强制归零 → camera_box ≡ interp-only
        tgt = raw_off[i] * w[i]
        step = np.clip(tgt - curv, np.array([-max_vc, -max_vc, -max_vs, -max_vs]),
                       np.array([max_vc, max_vc, max_vs, max_vs]))
        curv[0] += args.off_alpha * step[0]
        curv[1] += args.off_alpha * step[1]
        curv[2] += args.off_alpha_size * step[2]
        curv[3] += args.off_alpha_size * step[3]
        off[i] = curv
    for rec in track:
        i = rec["frame"]
        cb = smooth[i] + off[i]
        rec["camera_box"] = [round(float(v), 1) for v in cb]

    # ── 4. 空间状态层（MD3 v2：底部1/3区域重叠率 ≥50% + 1.5s 迟滞）──────
    # v1 脚点单点判定对画面边缘裁切脆弱（猫框底边贴画面底边时永不命中）
    min_hold = int(fps * args.hold_sec)
    state, pending, pending_cnt = "on floor", None, 0
    states = []
    for rec in track:
        i = rec["frame"]
        furn = furn_at[min(fs, key=lambda f: abs(f - i))] if fs else []
        x1, y1, x2, y2 = rec["box"]
        bh = y2 - y1
        zone = (x1, y2 - bh / 3, x2, y2)  # 猫框底部 1/3（支撑接触区）
        za = max(1.0, (zone[2] - zone[0]) * (zone[3] - zone[1]))
        cur, best_r, best_lab = "on floor", 0.0, None
        for lab, fb, _sc in furn:
            ix = max(0.0, min(zone[2], fb[2]) - max(zone[0], fb[0]))
            iy = max(0.0, min(zone[3], fb[3]) - max(zone[1], fb[1]))
            r = (ix * iy) / za
            if r >= 0.5 and r > best_r:
                best_r, best_lab = r, lab
        if best_lab:
            cur = f"cat on {best_lab}"
        if cur == state:
            pending, pending_cnt = None, 0
        else:
            if pending == cur:
                pending_cnt += 1
            else:
                pending, pending_cnt = cur, 1
            if pending_cnt >= min_hold:
                state = cur
        rec["state"] = state
        states.append(state)

    # ── 5. 落盘（design B3 契约）────────────────────────────────────
    report = {
        "video": args.video, "fps": fps, "frames": T,
        "sample_stride": args.sample_stride, "prompt": args.prompt,
        "sampled_detections": {
            str(f): {"cat_box": sampled[f]["cat"][0].tolist(),
                     "cat_conf": sampled[f]["cat"][1],
                     "furniture": furn_at[f]} for f in fs},
        "motion_corrected_frames": int(corrected.sum()),
        "motion_correct_ratio": round(float(corrected.mean()), 4),
        "interpolated_frames": int(interpolated.sum()),
        "interpolated_ratio": round(float(interpolated.mean()), 4),
        "smooth_track": track,
    }
    out_json = f"{args.out}/track.json"
    json.dump(report, open(out_json, "w"))
    print(f"TRACK DONE -> {out_json} | interp={report['interpolated_ratio']:.1%} "
          f"corrected={report['motion_correct_ratio']:.1%}", flush=True)


if __name__ == "__main__":
    main()
