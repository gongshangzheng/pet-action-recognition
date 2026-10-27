#!/usr/bin/env python3
"""GPU 空闲看门狗：轮询 nvidia-smi，记录状态；满足条件时执行（一次）指定命令。

用途：把「等 GPU 空闲再跑」自动化。看门狗只做一件事——判定空闲并在空闲时点火，
不抢占、不 kill 任何人的进程；命中条件默认要求**连续 N 次**满足，避免别人的任务间隙误判。

判定条件（全部满足才算空闲）：
  - 目标卡显存空闲 ≥ --min-free-mib（默认 12000 MiB）
  - 目标卡利用率 ≤ --max-util（默认 15%）
  - 连续 --consecutive 次（默认 3 次，间隔 --interval 秒）都满足

产物：
  <log>            每次轮询一行 JSON（时间、卡号、used/total、util）
  <state-dir>/GPU_FREE   命中时写入标记（内容 = 命中时间与卡号）
  <state-dir>/launch.log 被点火的命令输出

用法：
  # 只观察，不点火
  python3 scripts/checks/gpu_watcher.py --log results/gate/gpu_watch.jsonl --state-dir results/gate

  # 命中后执行一次（可重复 --on-free 串多步，会顺序执行并各自记日志）
  python3 scripts/checks/gpu_watcher.py ... --on-free "<shell command 1>" --on-free "<shell command 2>"

  # 立刻探一次（调试）
  python3 scripts/checks/gpu_watcher.py --once --log ...
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def query() -> list[dict]:
    command = ["nvidia-smi", "--query-gpu=index,memory.used,memory.total,utilization.gpu",
               "--format=csv,noheader,nounits"]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        return []
    cards = []
    for line in completed.stdout.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 4:
            continue
        cards.append({"index": int(parts[0]), "used": int(parts[1]), "total": int(parts[2]), "util": int(parts[3])})
    return cards


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--interval", type=int, default=120, help="轮询间隔秒（默认 120）")
    parser.add_argument("--min-free-mib", type=int, default=12000)
    parser.add_argument("--max-util", type=int, default=15)
    parser.add_argument("--consecutive", type=int, default=3)
    parser.add_argument("--timeout-hours", type=float, default=72.0, help="看门狗总时长上限，超时退出")
    parser.add_argument("--on-free", action="append", default=[], help="命中后顺序执行的 shell 命令（可多次）")
    parser.add_argument("--once", action="store_true", help="只探一次并打印判定")
    args = parser.parse_args()

    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.state_dir.mkdir(parents=True, exist_ok=True)
    free_marker = args.state_dir / "GPU_FREE"
    launch_log = args.state_dir / "launch.log"

    streak = 0
    started = time.time()
    deadline = started + args.timeout_hours * 3600

    while True:
        cards = query()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        available = [card for card in cards
                     if card["total"] - card["used"] >= args.min_free_mib and card["util"] <= args.max_util]
        record = {"time": now, "cards": cards, "free_cards": [card["index"] for card in available]}
        with args.log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

        streak = streak + 1 if available else 0
        summary = " ".join(f"gpu{card['index']}:{card['used']}/{card['total']}MiB {card['util']}%" for card in cards)
        print(f"[gpu_watcher] {now} {summary} | 空闲连击 {streak}/{args.consecutive}", flush=True)

        if args.once:
            print("[gpu_watcher] --once 模式：不点火，退出")
            return 0 if available else 1

        if streak >= args.consecutive:
            free_marker.write_text(json.dumps({"time": now, "free_cards": [card["index"] for card in available]},
                                              ensure_ascii=False) + "\n", encoding="utf-8")
            print(f"[gpu_watcher] 命中空闲条件，写入 {free_marker}", flush=True)
            for order, command in enumerate(args.on_free, 1):
                with launch_log.open("a", encoding="utf-8") as stream:
                    stream.write(f"\n===== {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} step {order}: {command}\n")
                    stream.flush()
                    completed = subprocess.run(command, shell=True, stdout=stream, stderr=subprocess.STDOUT,
                                               stdin=subprocess.DEVNULL)
                    stream.write(f"===== step {order} exit={completed.returncode}\n")
                print(f"[gpu_watcher] step {order} 退出码 {completed.returncode}", flush=True)
            print("[gpu_watcher] 全部步骤完成，看门狗退出", flush=True)
            return 0

        if time.time() > deadline:
            print("[gpu_watcher] 超过 timeout-hours，退出", flush=True)
            return 3
        time.sleep(args.interval)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        sys.exit(130)
