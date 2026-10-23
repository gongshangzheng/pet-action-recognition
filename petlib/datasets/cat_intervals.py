"""MMAction2 dataset, transform and metrics for labeled cat-video intervals."""
from __future__ import annotations

import json
import os.path as osp
from pathlib import Path

from mmcv.transforms import BaseTransform
from mmengine.evaluator import BaseMetric
from mmaction.datasets import VideoDataset
from mmaction.registry import DATASETS, METRICS, TRANSFORMS
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support


@DATASETS.register_module()
class IntervalVideoDataset(VideoDataset):
    """Read JSONL rows with video, label and 1-based inclusive frame bounds."""

    def load_data_list(self) -> list[dict]:
        rows = []
        with open(self.ann_file, encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                relative = Path(row["video"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError(f"Unsafe video path on line {line_number}: {relative}")
                start, end = int(row["start_frame"]), int(row["end_frame"])
                if start < 1 or end < start:
                    raise ValueError(f"Invalid frame range on line {line_number}")
                rows.append({
                    "filename": osp.join(self.data_prefix["video"], str(relative)),
                    "label": int(row["label"]),
                    "interval_start": start,
                    "interval_end": end,
                    "task_id": int(row["task_id"]),
                    "sample_id": row["sample_id"],
                })
        if not rows:
            raise ValueError(f"Empty interval dataset: {self.ann_file}")
        return rows


@TRANSFORMS.register_module()
class RestrictFrameRange(BaseTransform):
    """Make standard SampleFrames sample only inside the annotated interval."""

    def transform(self, results: dict) -> dict:
        start = int(results["interval_start"]) - 1
        end = int(results["interval_end"])
        source_frames = int(results["total_frames"])
        if start < 0 or end > source_frames or end <= start:
            raise ValueError(f"Interval [{start + 1}, {end}] exceeds {source_frames} frames: "
                             f"{results['filename']}")
        results["source_total_frames"] = source_frames
        results["total_frames"] = end - start
        results["start_index"] = start
        return results


@METRICS.register_module()
class CatIntervalMetric(BaseMetric):
    """Accuracy, class-wise measures and auditable interval predictions."""

    def __init__(self, classes: list[str], out_file: str, collect_device: str = "cpu") -> None:
        super().__init__(collect_device=collect_device)
        self.classes = classes
        self.out_file = out_file

    def process(self, data_batch, data_samples) -> None:
        for sample in data_samples:
            scores = sample.pred_score.detach().cpu().tolist()
            label = int(sample.gt_label.item())
            meta = sample.metainfo
            self.results.append({
                "sample_id": meta.get("sample_id"),
                "video": meta.get("filename"),
                "start_frame": meta.get("interval_start"),
                "end_frame": meta.get("interval_end"),
                "label": label,
                "predicted": max(range(len(scores)), key=scores.__getitem__),
                "scores": scores,
            })

    def compute_metrics(self, results: list[dict]) -> dict:
        truth = [row["label"] for row in results]
        predicted = [row["predicted"] for row in results]
        labels = list(range(len(self.classes)))
        precision, recall, f1, support = precision_recall_fscore_support(
            truth, predicted, labels=labels, zero_division=0)
        matrix = confusion_matrix(truth, predicted, labels=labels).tolist()
        accuracy = sum(a == b for a, b in zip(truth, predicted)) / len(truth)
        report = {
            "classes": self.classes,
            "samples": len(results),
            "top1_acc_percent": 100 * accuracy,
            "macro_f1_percent": 100 * float(f1.mean()),
            "balanced_acc_percent": 100 * float(recall.mean()),
            "per_class": [dict(label=name, support=int(support[i]),
                               precision_percent=100 * float(precision[i]),
                               recall_percent=100 * float(recall[i]),
                               f1_percent=100 * float(f1[i]))
                          for i, name in enumerate(self.classes)],
            "confusion_matrix": matrix,
            "predictions": results,
        }
        output = Path(self.out_file)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"top1_acc": report["top1_acc_percent"],
                "macro_f1": report["macro_f1_percent"],
                "balanced_acc": report["balanced_acc_percent"]}
