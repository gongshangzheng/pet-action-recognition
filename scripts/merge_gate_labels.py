#!/usr/bin/env python3
"""合并多份门控原生标注（不同分块配置），按统一阈值出三态标签。

为什么需要：全量标注分两段跑（`--tiles 3` 跑了 70% 被主机负载拖停，剩余用 `--tiles 2` 补齐），
两份文件的判定阈值/配置不同；分数都存着，所以可以**离线重标定**，不需要重跑推理。

规则（写死，避免事后挑阈值）：
  cat ≥ --threshold                 → cat_present
  cat < threshold 且 dog ≥ threshold → other_animal_only
  否则                               → absent
另外记录 `config`（tiles）与 `score_cat/score_dog`，便于后续按配置做差异分析。

用法：
  python3 scripts/merge_gate_labels.py --threshold 0.15 \
      --in results/gate/labels_native_full_t3.jsonl --in results/gate/labels_native_remaining_t2.jsonl \
      --out results/gate/labels_native_all.jsonl
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path


def classify(cat: float, dog: float, threshold: float) -> str:
    if cat >= threshold:
        return "cat_present"
    if dog >= threshold:
        return "other_animal_only"
    return "absent"


def collapse(label: str) -> str:
    """门控只关心「有没有宠物」：猫和其他宠物都算 present。"""
    return "absent" if label == "absent" else "present"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="inputs", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--binary", action="store_true",
                        help="折叠为二态：present（猫或其他宠物）/ absent；原三态保留在 audit_label 字段")
    args = parser.parse_args()

    merged: dict[str, dict] = {}
    dup = 0
    for path in args.inputs:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                row = json.loads(line)
                if "error" in row:
                    continue
                key = row["path"]
                if key in merged:
                    dup += 1
                    # 不同配置重复出现时保留 cat 分数更高者（召回优先）
                    if (row.get("score_cat") or 0) <= (merged[key].get("score_cat") or 0):
                        continue
                row["audit_label"] = classify(row.get("score_cat") or 0.0, row.get("score_dog") or 0.0, args.threshold)
                row["label"] = collapse(row["audit_label"]) if args.binary else row["audit_label"]
                merged[key] = row

    counts = Counter(row["label"] for row in merged.values())
    by_config: dict[str, Counter] = {}
    audit_counter: Counter = Counter()
    for row in merged.values():
        config = f"tiles{row.get('tiles')}"
        by_config.setdefault(config, Counter())[row["label"]] += 1
        audit_counter[row.get("audit_label") or row["label"]] += 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as stream:
        for row in merged.values():
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")

    total = len(merged)
    print(f"合并 {len(args.inputs)} 份 → {total} 帧（重复 {dup} 条，保留 cat 分数更高者）；"
          f"阈值 {args.threshold}；{'二态' if args.binary else '三态'}")
    for label, count in counts.most_common():
        print(f"  {label:18s} {count:6d} ({count / total:.1%})")
    print(f"审计三态（未折叠）：{dict(audit_counter)}")
    print("按配置：")
    for config, counter in sorted(by_config.items()):
        n = sum(counter.values())
        print(f"  {config:8s} n={n:5d} cat {counter['cat_present']:5d} "
              f"dog {counter['other_animal_only']:5d} absent {counter['absent']:5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
