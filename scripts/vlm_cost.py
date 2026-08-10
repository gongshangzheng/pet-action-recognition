"""VLM 费用预估——发送前算视频 token + 梯度定价预算。

移植自 third-party/pet-videos/backend/services/token_calculator.py（Qwen3-VL 官方
smart_nframes/smart_resize/token 公式）+ estimate_service.py（estimate + breakdown）。
梯度定价复用 scripts/vlm_infer.PRICING_TIERS / _calc_cost，保证预估口径和实际计费一致。

用法：
  from scripts.vlm_cost import estimate
  est = estimate(video_path, fps=1.0, max_pixels=640*32*32, min_pixels=4*32*32,
                 prompt_length=2000)
  # est = {video_tokens, total_input_tokens, estimated_output_tokens,
  #        estimated_cost, breakdown:{input_cost, output_cost, input_details, output_details}, ...}

评测后对账：calc_cost_with_breakdown(actual_input_tokens, is_input=True)。
"""
from __future__ import annotations

import math
from typing import Dict, Tuple

import cv2

# Qwen3-VL 模型常量（官方）
FRAME_FACTOR = 2
IMAGE_FACTOR = 32  # 图像缩放因子
MAX_RATIO = 200  # 帧最大长宽比
VIDEO_MIN_PIXELS = 4 * 32 * 32
VIDEO_MAX_PIXELS = 640 * 32 * 32  # Qwen3-VL-Plus 像素上限
FPS_MIN_FRAMES = 4
FPS_MAX_FRAMES = 2000
VIDEO_TOTAL_PIXELS = 131072 * 32 * 32  # 总像素上限

# 复用 vlm_infer 的梯度定价（保证预估口径和实际 cost 一致）
from scripts.vlm_infer import PRICING_TIERS  # noqa: E402


def _round_by_factor(n: int, f: int) -> int:
    return round(n / f) * f


def _ceil_by_factor(n: int, f: int) -> int:
    return math.ceil(n / f) * f


def _floor_by_factor(n: int, f: int) -> int:
    return math.floor(n / f) * f


def get_video_info(video_path: str) -> Tuple[int, int, int, float]:
    """cv2 取 (height, width, total_frames, fps)。"""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"无法打开视频: {video_path}")
    try:
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        return h, w, total, fps
    finally:
        cap.release()


def smart_nframes(fps: float, total_frames: int, video_fps: float,
                  min_frames: int = FPS_MIN_FRAMES,
                  max_frames: int = FPS_MAX_FRAMES) -> int:
    """官方抽帧数算法。"""
    min_frames = _ceil_by_factor(min_frames, FRAME_FACTOR)
    max_frames = _floor_by_factor(min(max_frames, total_frames), FRAME_FACTOR)
    duration = total_frames / video_fps if video_fps != 0 else 0
    if duration - int(duration) > (1 / fps):
        total_frames = math.ceil(duration * video_fps)
    else:
        total_frames = math.ceil(int(duration) * video_fps)
    nframes = total_frames / video_fps * fps if video_fps else min_frames
    nframes = int(min(min(max(nframes, min_frames), max_frames), total_frames))
    if not (FRAME_FACTOR <= nframes <= total_frames):
        raise ValueError(f"nframes 应在 [{FRAME_FACTOR}, {total_frames}]，得到 {nframes}")
    return nframes


def smart_resize(h: int, w: int, nframes: int,
                 min_pixels: int = VIDEO_MIN_PIXELS,
                 max_pixels: int = VIDEO_MAX_PIXELS,
                 factor: int = IMAGE_FACTOR,
                 total_pixels: int = None) -> Tuple[int, int]:
    """官方智能调帧尺寸。"""
    if total_pixels is None:
        total_pixels = VIDEO_TOTAL_PIXELS
    if total_pixels > VIDEO_TOTAL_PIXELS * 10:  # 高分辨率模式
        max_pixels_per_frame = max(max_pixels, int(min_pixels * 1.05))
    else:
        max_pixels_per_frame = max(
            min(max_pixels, total_pixels / nframes * FRAME_FACTOR),
            int(min_pixels * 1.05))
    if max(h, w) / min(h, w) > MAX_RATIO:
        raise ValueError(f"长宽比超 {MAX_RATIO}: {max(h,w)/min(h,w)}")
    h_bar = max(factor, _round_by_factor(h, factor))
    w_bar = max(factor, _round_by_factor(w, factor))
    if h_bar * w_bar > max_pixels_per_frame:
        beta = math.sqrt((h * w) / max_pixels_per_frame)
        h_bar = _floor_by_factor(h / beta, factor)
        w_bar = _floor_by_factor(w / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (h * w))
        h_bar = _ceil_by_factor(h * beta, factor)
        w_bar = _ceil_by_factor(w * beta, factor)
    return h_bar, w_bar


def calculate_video_tokens(video_path: str, fps: float,
                           min_pixels: int = VIDEO_MIN_PIXELS,
                           max_pixels: int = VIDEO_MAX_PIXELS,
                           total_pixels: int = None) -> Dict:
    """官方算法算视频 token 数。"""
    h, w, total_frames, video_fps = get_video_info(video_path)
    nframes = smart_nframes(fps, total_frames, video_fps)
    rh, rw = smart_resize(h, w, nframes, min_pixels, max_pixels, IMAGE_FACTOR, total_pixels)
    video_token = int(math.ceil(nframes / 2) * rh / 32 * rw / 32)
    video_token += 2  # <|vision_bos|> / <|vision_eos|>
    return {
        "original_resolution": f"{h}x{w}",
        "resized_resolution": f"{rh}x{rw}",
        "total_frames": total_frames,
        "video_fps": round(video_fps, 2),
        "extracted_frames": nframes,
        "video_tokens": video_token,
        "tokens_per_frame": round(video_token / nframes, 2) if nframes else 0,
    }


def calc_cost_with_breakdown(tokens: int, is_input: bool = True) -> Dict:
    """梯度定价（带 breakdown，不四舍五入），移植自 EstimateService。"""
    total = 0.0
    remaining = tokens
    details = []
    for tier in PRICING_TIERS:
        tmin, tmax = tier["range"]
        price = tier["input_price"] if is_input else tier["output_price"]
        if remaining <= 0 or tokens <= tmin:
            continue
        if tokens <= tmax:
            in_tier = min(remaining, tokens - tmin)
        else:
            in_tier = tmax - max(tmin, tokens - remaining)
        tier_cost = (in_tier / 1000) * price
        total += tier_cost
        details.append({
            "tier": tier["name"], "range": f"{tmin//1000}K-{tmax//1000}K",
            "tokens_in_tier": in_tier, "price_per_1k": price, "tier_cost": tier_cost,
        })
        remaining -= in_tier
        if remaining <= 0:
            break
    return {"total_cost": total, "breakdown": details}


def estimate(video_path: str, fps: float = 1.0,
             max_pixels: int = VIDEO_MAX_PIXELS,
             min_pixels: int = VIDEO_MIN_PIXELS,
             prompt_length: int = 2000,
             estimated_output_tokens: int = 500,
             total_pixels: int = None) -> Dict:
    """发送前预估 token + 费用 + breakdown。

    Args:
        prompt_length: 提示词 token 数（_build_prompt 的 400 类名列表约 2000 token）
        estimated_output_tokens: 输出保守估计（默认 500）
    """
    tok_info = calculate_video_tokens(video_path, fps, min_pixels, max_pixels, total_pixels)
    video_tokens = tok_info["video_tokens"]
    total_input = video_tokens + prompt_length
    in_bd = calc_cost_with_breakdown(total_input, is_input=True)
    out_bd = calc_cost_with_breakdown(estimated_output_tokens, is_input=False)
    return {
        "video_tokens": video_tokens,
        "prompt_tokens": prompt_length,
        "total_input_tokens": total_input,
        "estimated_output_tokens": estimated_output_tokens,
        "estimated_total_tokens": total_input + estimated_output_tokens,
        "estimated_cost": round(in_bd["total_cost"] + out_bd["total_cost"], 6),
        "breakdown": {
            "input_cost": round(in_bd["total_cost"], 6),
            "output_cost": round(out_bd["total_cost"], 6),
            "input_details": in_bd["breakdown"],
            "output_details": out_bd["breakdown"],
        },
        "video_info": {
            "original_resolution": tok_info["original_resolution"],
            "resized_resolution": tok_info["resized_resolution"],
            "total_frames": tok_info["total_frames"],
            "video_fps": tok_info["video_fps"],
            "extracted_frames": tok_info["extracted_frames"],
            "tokens_per_frame": tok_info["tokens_per_frame"],
        },
    }


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="VLM 费用预估（单视频）")
    ap.add_argument("video")
    ap.add_argument("--fps", type=float, default=1.0)
    ap.add_argument("--prompt-length", type=int, default=2000)
    ap.add_argument("--max-pixels", type=int, default=VIDEO_MAX_PIXELS)
    ap.add_argument("--min-pixels", type=int, default=VIDEO_MIN_PIXELS)
    a = ap.parse_args()
    print(json.dumps(estimate(a.video, a.fps, a.max_pixels, a.min_pixels,
                              a.prompt_length), indent=2, ensure_ascii=False))
