#!/usr/bin/env python3
"""按报告页同一规则校验 `management/experiments/` 的每篇实验报告。

报告完整度由 `server/parsers/experiments_parser.report_problems` 判定（前端与生成脚本共用
同一份规则）。本脚本把它暴露成命令行入口：合并报告、新增报告后跑一次，incomplete 即失败。

用法：
  python3 scripts/checks/check_experiment_reports.py            # 校验，任一 incomplete 非零退出
  python3 scripts/checks/check_experiment_reports.py --verbose  # 同时打印每篇的章节模板与状态
  python3 scripts/checks/check_experiment_reports.py --json     # 机器可读结果

判据来源：`openspec/changes/experiment-report-consolidation/specs/experiment-report-catalog/spec.md`
「合并后的完整度可判定」。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.parsers.experiments_parser import (  # noqa: E402
    list_experiments,
    report_problems,
)

EXPERIMENTS_DIR = ROOT / "management/experiments"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true", help="打印每篇的模板与状态")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--root", default=str(EXPERIMENTS_DIR), help="报告根目录")
    args = parser.parse_args()

    root = Path(args.root)
    listing = list_experiments(str(root))

    rows = []
    for report in listing["reports"]:
        detail = report_problems(
            str(root / report["topic"] / report["slug"]),
        )[0] or {}
        rows.append({
            "topic": report["topic"],
            "slug": report["slug"],
            "title": report["title"],
            "status": report["status"],
            "verdict": report["verdict"],
            "template": report.get("template", detail.get("template", "")),
            "incomplete": report["incomplete"],
            "problems": report["problems"],
        })
    for missing in listing["invalid"]:
        rows.append({
            "topic": missing["topic"],
            "slug": missing["slug"],
            "title": "",
            "status": "",
            "verdict": "",
            "template": "",
            "incomplete": True,
            "problems": missing["missing"],
        })

    failed = [r for r in rows if r["incomplete"]]

    if args.json:
        print(json.dumps({"reports": rows, "failed": len(failed)}, ensure_ascii=False, indent=2))
    else:
        for row in rows:
            mark = "FAIL" if row["incomplete"] else "ok  "
            line = f"{mark} {row['topic']}/{row['slug']} [{row['status']}/{row['verdict']}]"
            if args.verbose and row["template"]:
                line += f" template={row['template']}"
            print(line)
            if row["incomplete"]:
                for problem in row["problems"]:
                    print(f"       - {problem}")
        print(f"\n{len(rows)} 篇，{len(rows) - len(failed)} 篇完整，{len(failed)} 篇 incomplete")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
