"""从已有 `pet.highlight.v1` 载荷离线重算亮点参考候选（design D9，tasks 6.4）。

只用载荷里的 1 秒窗口汇总，不读视频、不跑模型、不用服务器。打印每个载荷的窗口分布
（身体占比 / 活动的分位数、各自达标与同时达标的秒数）和候选，用于判断默认阈值是否合适。

  python scripts/recompute_highlight_candidates.py results/highlights/demo/*.json
  python scripts/recompute_highlight_candidates.py x.json --highlight-area-ratio 0.03 --out-dir results/highlights/recompute

--out-dir 时写出带 `highlight_candidates` 的载荷副本（不覆盖输入文件）。
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from petlib.highlights.aggregate import HighlightConfig  # noqa: E402
from petlib.highlights.candidates import _qualifies, find_candidates, highlight_rule  # noqa: E402
from petlib.highlights.report import SCHEMA  # noqa: E402

sys.path.insert(0, str(REPO / "scripts"))
from extract_highlight_features import add_highlight_args, highlight_kwargs  # noqa: E402


def config_for(payload: dict, overrides: dict) -> HighlightConfig:
    """载荷里记录的分析参数（不含亮点阈值）+ 命令行给出的亮点阈值。"""
    fields = {f.name for f in dataclasses.fields(HighlightConfig)}
    saved = payload.get("analysis", {}).get("config", {}) or {}
    kw = {k: (tuple(v) if isinstance(v, list) else v) for k, v in saved.items()
          if k in fields and not k.startswith("highlight_")}
    kw.update(overrides)
    return HighlightConfig(**kw)


def quantiles(vals: list[float]) -> str:
    if not vals:
        return "-"
    v = sorted(vals)
    pick = lambda q: v[min(len(v) - 1, int(q * (len(v) - 1) + 0.5))]  # noqa: E731
    return f"p50={pick(0.5):.3f} p90={pick(0.9):.3f} max={v[-1]:.3f}"


def describe(payload: dict, cfg: HighlightConfig) -> list[str]:
    wins = payload.get("windows", [])
    pet = [w for w in wins if w.get("body_area_ratio_mean") is not None]
    areas = [w["body_area_ratio_mean"] for w in pet]
    acts = [w["activity_mean"] for w in pet if w.get("activity_mean") is not None]
    sec = lambda ws: sum(w["t_end"] - w["t_start"] for w in ws)  # noqa: E731
    area_ok = [w for w in pet if w["body_area_ratio_mean"] >= cfg.highlight_area_ratio]
    act_ok = [w for w in pet if (w.get("activity_mean") or 0) >= cfg.highlight_activity]
    both = [w for w in wins if _qualifies(w, cfg)]
    return [f"  windows={len(wins)} with_pet={len(pet)}",
            f"  body_area: {quantiles(areas)} | >= {cfg.highlight_area_ratio}: {sec(area_ok):.0f}s",
            f"  activity : {quantiles(acts)} | >= {cfg.highlight_activity}: {sec(act_ok):.0f}s",
            f"  both     : {sec(both):.0f}s"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("payloads", nargs="+", help="pet.highlight.v1 载荷 JSON")
    ap.add_argument("--out-dir", help="写出带候选的载荷副本（不覆盖输入）")
    add_highlight_args(ap, HighlightConfig())
    args = ap.parse_args(argv)
    overrides = highlight_kwargs(args)
    out_dir = Path(args.out_dir) if args.out_dir else None

    total = 0
    for p in map(Path, args.payloads):
        payload = json.loads(p.read_text(encoding="utf-8"))
        if payload.get("schema") != SCHEMA or "windows" not in payload:
            print(f"SKIP {p.name}: not a {SCHEMA} payload with windows")
            continue
        cfg = config_for(payload, overrides)
        duration = float(payload.get("source", {}).get("duration_sec") or payload["summary"]["duration_sec"])
        cands = find_candidates(payload["windows"], duration, cfg)
        total += len(cands)
        print(f"{p.name}  duration={duration:.1f}s  candidates={len(cands)}")
        for line in describe(payload, cfg):
            print(line)
        for c in cands:
            act = c["action"]["label"] if c["action"] else "-"
            print(f"  #{c['rank']} {c['t_start']:.1f}-{c['t_end']:.1f}s score={c['score']:.3f} "
                  f"area={c['body_area_ratio_mean']:.3f} activity={c['activity_mean']:.3f} "
                  f"face={c['face_exposed_sec']:.1f}s action={act}")
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            dst = out_dir / p.name
            if dst.resolve() == p.resolve():
                raise SystemExit(f"refusing to overwrite input {p}")
            payload["highlight_candidates"] = cands
            payload.setdefault("analysis", {})["highlight_rule"] = {**highlight_rule(cfg), "offline_recompute": True}
            dst.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"RECOMPUTE DONE payloads={len(args.payloads)} candidates={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
