"""物种感知跟踪：猫流/狗流各一个 tracker 实例，输出合并 track id。

multi-pet-sort-tracking design 4.5：不修改 tracker 内部匹配代价，
跨物种交换在结构上不可能——每个物种的检测只进自己实例的流。

track id 合并规则：cat 流保留原 id；dog 流 id 偏移 +SPECIES_ID_OFFSET，
保证两流 id 不碰撞且可从 id 反推物种。
"""
from __future__ import annotations

from petlib.schemas import Detection, Track
from petlib.tracking.base import Tracker

SPECIES_ID_OFFSET = 10_000
TRACKED_SPECIES = ("cat", "dog")


class SpeciesSplitTracker(Tracker):
    """按物种拆分检测流到多个内层 tracker 实例。"""

    name = "species_split"

    def __init__(self, tracker_factory, cfg: dict):
        """tracker_factory：接受 cfg dict 的可调用（如 lambda c: OCSortTracker(**c)）。"""
        self._factories = {s: (lambda f=tracker_factory: f(dict(cfg))) for s in TRACKED_SPECIES}
        self._inner: dict[str, Tracker] = {}
        self._cfg = dict(cfg)

    def _tracker_for(self, species: str) -> Tracker:
        if species not in self._inner:
            self._inner[species] = self._factories[species]()
        return self._inner[species]

    def update(self, detections: list[Detection], frame_idx: int,
               frame=None) -> list[Track]:
        out: list[Track] = []
        for species in TRACKED_SPECIES:
            subset = [d for d in detections if d.cls == species]
            if not subset and species not in self._inner:
                continue  # 该物种从未出现，不建实例
            tracks = self._tracker_for(species).update(subset, frame_idx)
            out.extend(self._offset_ids(tracks, species))
        return out

    def _offset_ids(self, tracks: list[Track], species: str) -> list[Track]:
        if species == "cat":
            return tracks
        offset_tracks: list[Track] = []
        for t in tracks:
            offset_tracks.append(Track(SPECIES_ID_OFFSET + t.track_id, t.boxes))
        return offset_tracks

    def finalize(self) -> list[Track]:
        merged: list[Track] = []
        for species in self._inner:
            merged.extend(self._offset_ids(self._inner[species].finalize(), species))
        return sorted(merged, key=lambda t: t.track_id)
