"""VLM 推理原语——用 Qwen3-VL-Plus(DashScope) 对视频做动作识别。

移植自 third-party/pet-videos/backend/services/dashscope_service.py（纯 SDK wrapper）+
estimate_service.py（3 级梯度定价）。返回 shape 对齐 scripts/_infer.py:infer_and_annotate，
使 run_test_vlm.py 能写和 mmaction2 同结构的 test_results.json 条目。

vlm_recognize(video_path, labels, ...) -> {top1_label, top1_score, top5, model_response,
                                          input_tokens, output_tokens, total_tokens, cost_cny, duration_sec}
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Optional

# Qwen3-VL-Plus 梯度定价（元/1k tokens，不四舍五入；移植自 pet-videos config.PRICING_TIERS）
PRICING_TIERS = [
    {"name": "0-32K", "range": (0, 32_000), "input_price": 0.001, "output_price": 0.01},
    {"name": "32K-128K", "range": (32_000, 128_000), "input_price": 0.0015, "output_price": 0.015},
    {"name": "128K-256K", "range": (128_000, 256_000), "input_price": 0.003, "output_price": 0.03},
]


def _calc_cost(tokens: int, is_input: bool) -> float:
    """梯度定价成本（元），移植自 EstimateService.calculate_cost_by_tier。"""
    if tokens <= 0:
        return 0.0
    total = 0.0
    remaining = tokens
    for tier in PRICING_TIERS:
        tmin, tmax = tier["range"]
        price = tier["input_price"] if is_input else tier["output_price"]
        if remaining <= 0 or tokens <= tmin:
            continue
        if tokens <= tmax:
            in_tier = min(remaining, tokens - tmin)
        else:
            in_tier = tmax - max(tmin, tokens - remaining)
        total += (in_tier / 1000) * price
        remaining -= in_tier
        if remaining <= 0:
            break
    return total


def _norm_tokens(s: str) -> tuple:
    """类名归一化（移植自 speedrun._norm_tokens）：camelCase 拆 + 非字母数字拆 + lowercase + 排序。"""
    s = re.sub(r"(.)([A-Z][a-z])", r"\1 \2", s)
    s = re.sub(r"([a-z])([A-Z])", r"\1 \2", s)
    toks = [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t]
    return tuple(sorted(toks))


def _build_prompt(labels: list[str], top_k: int = 5) -> str:
    """让 VLM 从 label 列表里选 top-k，输出 JSON。"""
    # 列全部类名，确保 GT 类在选项里（K400=400 类，截 200 会让后 200 类注定丢分）
    full = "\n".join(f"- {l}" for l in labels)
    return (
        "Watch this video carefully and identify the main human/pet action happening. "
        f"Choose the {top_k} most likely actions from this list (most likely first):\n{full}\n\n"
        f'Respond ONLY with a JSON object: {{"actions": ["action_name_1", "action_name_2", ...]}} '
        "where each name is EXACTLY from the list above, most likely first. No other text."
    )


def _parse_actions(text: str, labels: list[str], top_k: int = 5) -> list[str]:
    """从 VLM 文本响应解析出 top-k label 名（fuzzy-match 到 label 列表）。"""
    # 提取 JSON 块（可能有 ```json fence）
    m = re.search(r"\{.*\}", text, re.DOTALL)
    names: list[str] = []
    if m:
        try:
            obj = json.loads(m.group(0))
            raw = obj.get("actions") or obj.get("action") or []
            if isinstance(raw, str):
                raw = [raw]
            names = [str(x) for x in raw][:top_k]
        except json.JSONDecodeError:
            pass
    if not names:
        # 退化为按行/逗号拆
        cleaned = text.strip().strip("`")
        names = [n.strip().strip('"').strip("'") for n in re.split(r"[,\n]", cleaned) if n.strip()][:top_k]

    # fuzzy-match 每个 VLM 输出名 → label 列表里的一个
    label_by_norm = {}
    for l in labels:
        label_by_norm.setdefault(_norm_tokens(l), l)
    matched: list[str] = []
    for n in names:
        key = _norm_tokens(n)
        if key in label_by_norm:
            matched.append(label_by_norm[key])
        else:
            # 找 token 重叠最多的 label（subsume 关系）
            best = None
            best_overlap = 0
            for l in labels:
                lt = set(_norm_tokens(l))
                overlap = len(set(key) & lt)
                if overlap > best_overlap:
                    best_overlap = overlap
                    best = l
            if best and best_overlap > 0:
                matched.append(best)
    # 去重保序
    seen = set()
    uniq = [m for m in matched if not (m in seen or seen.add(m))]
    return uniq[:top_k]


def vlm_recognize(
    video_path: str,
    labels: list[str],
    fps: float = 1.0,
    max_pixels: int = 640 * 32 * 32,
    min_pixels: int = 4 * 32 * 32,
    model_name: str = "qwen3-vl-plus",
    vl_high_resolution_images: bool = False,
    api_key: Optional[str] = None,
    top_k: int = 5,
) -> dict:
    """对单视频跑 VLM 识别，返回对齐 infer_and_annotate 的 shape + token/成本。

    Args:
        video_path: 视频文件路径（DashScope 以 file:// 读本地文件，需 pet 本地可达）。
        labels: 类名列表（index=行号，mmaction2 约定）。
        fps/max_pixels/min_pixels: DashScope 视频抽帧参数。
        model_name: DashScope 模型名（默认 qwen3-vl-plus）。
        api_key: DASHSCOPE_API_KEY；None 则读 env。
        top_k: 让 VLM 输出 top-k。

    Returns:
        {top1_label, top1_score, top5, model_response, input_tokens, output_tokens,
         total_tokens, cost_cny, duration_sec, error?}
    """
    key = api_key or os.environ.get("DASHSCOPE_API_KEY")
    if not key or key == "your-api-key-here":
        return {"error": "DASHSCOPE_API_KEY 未配置（env DASHSCOPE_API_KEY）", "top1_label": None}

    try:
        from dashscope import MultiModalConversation
    except ImportError:
        return {"error": "dashscope SDK 未装（pip install dashscope）", "top1_label": None}

    prompt = _build_prompt(labels, top_k=top_k)
    video_url = f"file://{video_path}"  # 不 urlencode（移植自 pet-videos，必须如此）
    messages = [{
        "role": "user",
        "content": [
            {"video": video_url, "fps": fps, "max_pixels": max_pixels, "min_pixels": min_pixels},
            {"text": prompt},
        ],
    }]

    t0 = time.time()
    try:
        resp = MultiModalConversation.call(
            api_key=key,
            model=model_name,
            messages=messages,
            vl_high_resolution_images=vl_high_resolution_images,
        )
    except Exception as e:
        return {"error": f"DashScope 调用异常: {e}", "top1_label": None, "duration_sec": round(time.time() - t0, 1)}

    duration = round(time.time() - t0, 1)
    if resp.status_code != 200:
        return {"error": f"API status {resp.status_code}: {getattr(resp, 'message', '')}",
                "top1_label": None, "duration_sec": duration}

    usage = resp.usage
    in_tok = getattr(usage, "input_tokens", 0) or 0
    out_tok = getattr(usage, "output_tokens", 0) or 0
    tot_tok = getattr(usage, "total_tokens", in_tok + out_tok) or (in_tok + out_tok)
    cost = round(_calc_cost(in_tok, True) + _calc_cost(out_tok, False), 6)

    text = resp.output.choices[0].message.content[0]["text"]
    matched = _parse_actions(text, labels, top_k=top_k)
    top1 = matched[0] if matched else ""
    top5 = [(lbl, 0.0) for lbl in matched]  # VLM 无概率，score 占位 0.0

    return {
        "top1_label": top1,
        "top1_score": 1.0 if top1 else 0.0,
        "top5": top5,
        "model_response": text,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": tot_tok,
        "cost_cny": cost,
        "duration_sec": duration,
    }


if __name__ == "__main__":
    # CLI smoke：python scripts/vlm_infer.py <video> <label_map>
    import sys
    from _infer import load_labels  # 复用 mmaction2 label 加载
    vp, lp = sys.argv[1], sys.argv[2]
    lbls = load_labels(lp)
    r = vlm_recognize(vp, lbls)
    print(json.dumps(r, ensure_ascii=False, indent=2))
