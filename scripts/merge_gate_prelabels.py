#!/usr/bin/env python3
"""Attach verified teacher suggestions to a review set without changing human labels."""
import argparse
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("predictions", type=Path)
    args = parser.parse_args()
    metadata_path = args.review / "items.json"
    data = json.loads(metadata_path.read_text(encoding="utf-8"))
    items = data["items"]
    predictions = {}
    with args.predictions.open(encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record.get("error"):
                raise ValueError(f"prediction failed: {record}")
            path = record["path"]
            if path in predictions:
                raise ValueError(f"duplicate prediction: {path}")
            predictions[path] = record
    if len(items) != len(predictions) or set(predictions) != {x["path"] for x in items}:
        raise ValueError("predictions do not exactly match review items")
    for item in items:
        result = predictions[item["path"]]
        if result["video"] != item["video"] or result["frame_idx"] != item["frame_idx"]:
            raise ValueError(f"source mismatch: {item['path']}")
        if result["native_width"] != item["native_width"] or result["native_height"] != item["native_height"]:
            raise ValueError(f"image size mismatch: {item['path']}")
        item["teacher_label"] = result["label"]
        for name in ("cat", "dog"):
            item[f"score_{name}"] = result[f"score_{name}"]
            box = result[f"box_{name}"]
            if box is not None:
                sx = item["width"] / item["native_width"]
                sy = item["height"] / item["native_height"]
                box = [box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy]
            item[f"box_{name}"] = box
    data["hide_teacher"] = False
    temporary = metadata_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, metadata_path)
    print(f"attached {len(items)} suggestions; human labels untouched")


if __name__ == "__main__":
    main()
