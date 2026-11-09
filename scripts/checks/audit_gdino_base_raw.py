#!/usr/bin/env python3
"""Audit a completed GDINO base raw run without modifying its inputs."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

WEIGHT = "5548f844c928c4b6f411fa8cbcc2bfa8dbbba437cb1d513975519f93c2a9ed21"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--run-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    run = args.run_dir
    meta = json.loads((run / "manifest.json").read_text())
    manifest = run / "videos.txt"
    videos = manifest.read_text().splitlines()
    ledger = json.loads((run / "source-failures.json").read_text())
    root = Path(meta["video_root"])
    cache = Path(meta["asset_root"]) / "detections"
    errors, warnings, rows = [], [], []
    def require(condition, message):
        if not condition:
            errors.append(message)
    require(len(videos) == 2737 and len(set(videos)) == 2737 and len({Path(v).stem for v in videos}) == 2737, "manifest count/uniqueness")
    require(sha(manifest) == meta["video_list_sha256"] == ledger["manifest_sha256"], "manifest hash")
    require(meta.get("weight_sha256") == WEIGHT and meta.get("stride") == 5 and meta.get("raw_candidates_version") == 1 and meta.get("box_threshold") == 0.3 and meta.get("text_threshold") == 0.3, "manifest model/config")
    failures = ledger["failures"]
    failed = {entry["video"] for entry in failures}
    require(ledger.get("schema") == "gdino-source-failures-v1" and ledger.get("checked") == 2737 and len(failures) == len(failed) == 14 and failed <= set(videos), "ledger identities")
    for entry in failures:
        source = root / entry["video"]
        require(entry.get("status") == "source_unreadable" and bool(entry.get("error")) and source.stat().st_size == entry.get("size_bytes") and sha(source) == entry.get("source_sha256"), f"ledger fingerprint {entry['video']}")
    expected = {Path(v).stem + ".json" for v in videos if v not in failed}
    actual = {x.name for x in cache.glob("*.json")}
    require(expected == actual, f"cache sets missing={sorted(expected-actual)} extra={sorted(actual-expected)}")
    writing = sorted(str(x) for x in cache.rglob("*.writing*"))
    require(not writing, f"writing files {writing}")
    for video in videos:
        if video in failed:
            continue
        path = cache / (Path(video).stem + ".json")
        if not path.is_file():
            continue
        try:
            d = json.loads(path.read_text())
            fp = d["fingerprint"]
            n = d["decoded_frames"]
            anchors = d["anchors"]
            require(d.get("schema") == "cat-crop-detection-v2" and d.get("status") == "complete" and d.get("video") == video and d.get("source_path") == str(root / video), f"identity {video}")
            require(isinstance(d.get("source_sha256"), str) and re.fullmatch(r"[0-9a-f]{64}", d["source_sha256"]) is not None and d.get("source_bytes") == (root / video).stat().st_size, f"source fingerprint {video}")
            require(all(fp.get(k) == v for k, v in {"weights_sha256": WEIGHT, "weights_bytes": 933400872, "raw_candidates_version": 1, "sample_stride": 5, "box_threshold": 0.3, "text_threshold": 0.3, "classes": ["cat", "dog"]}.items()), f"fingerprint {video}")
            require(d.get("sample_stride") == 5 and d.get("box_threshold") == 0.3 and d.get("text_threshold") == 0.3 and d.get("classes") == ["cat", "dog"], f"config {video}")
            require(isinstance(n, int) and n > 0 and list(anchors) == [str(x) for x in range(0, n, 5)] and d.get("sampled_frames") == len(anchors), f"anchors {video}")
            counts = {"cat": 0, "dog": 0, "empty": 0}
            for frame, anchor in anchors.items():
                raw = anchor["raw_candidates"]
                if not isinstance(raw, list):
                    raise ValueError(f"non-list raw {frame}")
                if not raw:
                    counts["empty"] += 1
                for item in raw:
                    cls, box, conf = item["class"], item["box"], item["confidence"]
                    valid = cls in ("cat", "dog") and isinstance(box, list) and len(box) == 4 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in box) and isinstance(conf, (int, float)) and math.isfinite(conf) and 0 <= conf <= 1
                    if not valid:
                        raise ValueError(f"invalid raw candidate frame {frame}")
                    counts[cls] += 1
            reported = d["properties"]["frame_count_reported"]
            if reported != n:
                warnings.append({"video": video, "reported": reported, "decoded": n})
            rows.append({"video": video, "decoded_frames": n, "sampled_frames": len(anchors), "source_sha256": d["source_sha256"], "raw_cat": counts["cat"], "raw_dog": counts["dog"], "empty_anchors": counts["empty"]})
        except (KeyError, TypeError, ValueError, OSError) as exc:
            errors.append(f"cache {video}: {exc}")
    statuses = []
    for start in range(0, len(videos), 64):
        count = min(64, len(videos) - start)
        paths = sorted(run.glob(f"all-{start}-{count}.resume-*.status.json"))
        original = run / f"all-{start}-{count}.status.json"
        if not paths and original.exists():
            paths = [original]
        if not paths:
            errors.append(f"missing batch {start}")
            continue
        path = paths[-1]
        status = json.loads(path.read_text())
        require(status.get("returncode") == 0 and status.get("start") == start and status.get("count") == count and status.get("phase") in ("detect", "source_failures_only"), f"batch status {path.name}")
        statuses.append({"path": path.name, **status})
    result = {"success": not errors, "manifest_count": len(videos), "completed": len(rows), "failed": failures, "missing_cache": sorted(expected-actual), "extra_cache": sorted(actual-expected), "writing": writing, "batch_statuses": statuses, "frame_count_warnings": warnings, "videos": rows, "errors": errors, "quality": "unaccepted"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"success": result["success"], "completed": len(rows), "failures": len(failures), "warnings": len(warnings), "batch_slots": len(statuses), "errors": errors}, ensure_ascii=False))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
