"""门控人工核验路由：列出 review set、取帧、写人工标注。

数据目录（`RESULTS_DIR/gate/review/<set>/`）：由 `scripts/prepare_gate_review_set.py` 生成

  <set>/items.json   教师判定 + 框 + 场景标签
  <set>/frames/...   帧文件
  <set>/labels.csv   人工标注（本路由写入；present / absent / uncertain）

只读 + 单字段写入；不修改 items.json，不改帧文件。
"""
from __future__ import annotations

import csv
import io
import json
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from server.config import BASE_DIR

router = APIRouter(prefix="/api/gate-review", tags=["gate-review"])

REVIEW_ROOT = os.path.join(BASE_DIR, "results", "gate", "review")
ALLOWED_LABELS = {"present", "absent", "uncertain"}
SAFE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _set_dir(name: str) -> str:
    """只允许 review 根目录下的直接子目录（防目录穿越）。"""
    if not name or "/" in name or "\\" in name or name in (".", ".."):
        raise HTTPException(status_code=400, detail="非法 set 名称")
    path = os.path.join(REVIEW_ROOT, name)
    if not os.path.isdir(path):
        raise HTTPException(status_code=404, detail=f"review set 不存在: {name}")
    return path


def _read_items(set_dir: str) -> dict:
    items_file = os.path.join(set_dir, "items.json")
    if not os.path.isfile(items_file):
        raise HTTPException(status_code=404, detail="items.json 缺失")
    with open(items_file, encoding="utf-8") as stream:
        return json.load(stream)


def _read_labels(set_dir: str) -> dict[str, dict]:
    path = os.path.join(set_dir, "labels.csv")
    if not os.path.isfile(path):
        return {}
    with open(path, encoding="utf-8", newline="") as stream:
        return {row["path"]: row for row in csv.DictReader(stream)}


@router.get("/sets")
def list_sets() -> list[dict]:
    if not os.path.isdir(REVIEW_ROOT):
        return []
    sets = []
    for name in sorted(os.listdir(REVIEW_ROOT)):
        path = os.path.join(REVIEW_ROOT, name)
        if not os.path.isdir(path) or not os.path.isfile(os.path.join(path, "items.json")):
            continue
        data = _read_items(path)
        labels = _read_labels(path)
        labeled = sum(1 for row in labels.values() if (row.get("human_label") or "").strip())
        sets.append({"name": name, "count": data.get("count", len(data.get("items", []))),
                     "labeled": labeled})
    return sets


@router.get("/sets/{name}/items")
def list_items(name: str, scenario: str | None = None, only_unlabeled: bool = False,
               page: int = 1, page_size: int = 24) -> dict:
    set_dir = _set_dir(name)
    data = _read_items(set_dir)
    labels = _read_labels(set_dir)
    items = []
    for item in data.get("items", []):
        human = (labels.get(item["path"], {}) or {}).get("human_label", "") or ""
        if scenario and item.get("scenario") != scenario:
            continue
        if only_unlabeled and human:
            continue
        items.append({**item, "human_label": human})
    total = len(items)
    start = max(0, (page - 1) * page_size)
    return {"total": total, "page": page, "page_size": page_size,
            "items": items[start:start + page_size]}


@router.get("/sets/{name}/stats")
def stats(name: str) -> dict:
    set_dir = _set_dir(name)
    data = _read_items(set_dir)
    labels = _read_labels(set_dir)
    counts = {"present": 0, "absent": 0, "uncertain": 0, "unlabeled": 0}
    by_scenario: dict[str, dict[str, int]] = {}
    for item in data.get("items", []):
        human = (labels.get(item["path"], {}) or {}).get("human_label", "") or ""
        key = human if human in ALLOWED_LABELS else "unlabeled"
        counts[key] += 1
        bucket = by_scenario.setdefault(item.get("scenario", "?"), {})
        bucket[key] = bucket.get(key, 0) + 1
    return {"total": len(data.get("items", [])), "counts": counts, "by_scenario": by_scenario}


@router.get("/sets/{name}/frame")
def frame(name: str, path: str) -> FileResponse:
    """按 items.json 里的相对路径取帧；拒绝任何越界路径。"""
    set_dir = _set_dir(name)
    items_file = os.path.join(set_dir, "items.json")
    allowed = set()
    with open(items_file, encoding="utf-8") as stream:
        for item in json.load(stream).get("items", []):
            allowed.add(item.get("file"))
    if path not in allowed:
        raise HTTPException(status_code=404, detail="该帧不在 review set 中")
    full = os.path.realpath(os.path.join(set_dir, path))
    if not full.startswith(os.path.realpath(set_dir) + os.sep) or \
            os.path.splitext(full)[1].lower() not in SAFE_SUFFIXES:
        raise HTTPException(status_code=400, detail="非法帧路径")
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="帧文件缺失")
    return FileResponse(full, media_type="image/jpeg")


class LabelPayload(BaseModel):
    path: str
    human_label: str
    note: str = ""


@router.post("/sets/{name}/label")
def set_label(name: str, payload: LabelPayload) -> dict:
    """写入单条人工标注（label ∈ present/absent/uncertain）；整表原子重写。"""
    if payload.human_label not in ALLOWED_LABELS:
        raise HTTPException(status_code=400, detail=f"非法标签: {payload.human_label}")
    set_dir = _set_dir(name)
    labels_path = os.path.join(set_dir, "labels.csv")
    items = {item["path"]: item for item in _read_items(set_dir).get("items", [])}
    if payload.path not in items:
        raise HTTPException(status_code=404, detail="该帧不在 review set 中")
    rows = _read_labels(set_dir)
    item = items[payload.path]
    rows[payload.path] = {
        "path": payload.path,
        "scenario": item.get("scenario", ""),
        "domain": item.get("domain", ""),
        "split": item.get("split", ""),
        "teacher_label": item.get("teacher_label", ""),
        "score_cat": item.get("score_cat", ""),
        "human_label": payload.human_label,
        "note": payload.note,
    }
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["path", "scenario", "domain", "split",
                                                "teacher_label", "score_cat", "human_label", "note"])
    writer.writeheader()
    for key in sorted(rows):
        writer.writerow(rows[key])
    tmp = labels_path + ".writing"
    with open(tmp, "w", encoding="utf-8", newline="") as stream:
        stream.write(buffer.getvalue())
    os.replace(tmp, labels_path)
    labeled = sum(1 for row in rows.values() if (row.get("human_label") or "").strip())
    return {"ok": True, "labeled": labeled, "total": len(items)}
