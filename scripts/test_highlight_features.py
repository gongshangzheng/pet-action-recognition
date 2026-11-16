#!/usr/bin/env python3
"""亮点抓取特征的单元测试：只用合成数据和假检测器，不跑任何模型。"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from petlib.highlights import metrics as M  # noqa: E402
from petlib.highlights.actions import (label_at, load_timeline, mark_review, merge_segments,  # noqa: E402
                                       sliding_windows)
from petlib.highlights.aggregate import HighlightConfig, flags_to_segments  # noqa: E402
from petlib.highlights.candidates import RULE_NAME, find_candidates, highlight_rule  # noqa: E402
from petlib.highlights.report import SCHEMA, extract_highlights, write_outbox  # noqa: E402
from petlib.highlights.sources import (FaceObservation, FaceSource, HaarCatFaceSource,  # noqa: E402
                                       NoFaceSource, NoPetSource, PetObservation, PetSource,
                                       TrackJsonPetSource, find_cat_face_cascade)

FPS = 15
W, H = 320, 240
SQ = 80  # 方块边长 → 面积占比 6400 / 76800 = 0.0833
VISIBLE = range(15, 45)  # 1.0 s – 3.0 s
FACE = range(30, 45)  # 2.0 s – 3.0 s
N_FRAMES = 60


def square_box(f: int) -> tuple[float, float, float, float]:
    x = 20 + (f - VISIBLE.start) * 4
    return (float(x), 80.0, float(x + SQ), 80.0 + SQ)


def write_synthetic_video(path: Path) -> None:
    import cv2

    wr = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), FPS, (W, H))
    assert wr.isOpened(), "cv2 VideoWriter (MJPG) unavailable"
    for f in range(N_FRAMES):
        img = np.full((H, W, 3), 30, dtype=np.uint8)
        if f in VISIBLE:
            x1, y1, x2, y2 = (int(v) for v in square_box(f))
            img[y1:y2, x1:x2] = 220
        wr.write(img)
    wr.release()


class FakePet(PetSource):
    name = "fake_pet"
    area_source = "box"

    def observe(self, frame_bgr, frame_index):
        return [PetObservation(box=square_box(frame_index))] if frame_index in VISIBLE else []


class FaceByFrame(FaceSource):
    """FACE 帧内在宠物框左上角给一个 40×40 的脸；帧号由 FakePet 的框反推（x1 = 20 + (f-15)*4）。"""

    name = "fake_face"

    def detect(self, frame_bgr, pet_boxes):
        if not pet_boxes:
            return []
        x1, y1 = pet_boxes[0][:2]
        frame = int(round((x1 - 20) / 4)) + VISIBLE.start
        return [FaceObservation(box=(x1, y1, x1 + 40, y1 + 40))] if frame in FACE else []


class MetricTests(unittest.TestCase):
    def test_brightness_and_contrast(self):
        flat = np.full((10, 10, 3), 128, dtype=np.uint8)
        y = M.luma(flat)
        self.assertAlmostEqual(M.brightness(y), 128 / 255, places=4)
        self.assertAlmostEqual(M.contrast_rms(y), 0.0, places=6)
        half = np.zeros((10, 10, 3), dtype=np.uint8)
        half[:, 5:] = 255
        y = M.luma(half)
        self.assertAlmostEqual(M.brightness(y), 0.5, places=3)
        self.assertAlmostEqual(M.contrast_rms(y), 0.5, places=3)
        self.assertAlmostEqual(M.contrast_spread(y), 1.0, places=3)

    def test_area_ratio_and_box_clipping(self):
        m = M.boxes_mask([(0, 0, 10, 10), (-5, -5, 5, 5)], (100, 100))
        self.assertAlmostEqual(M.area_ratio(m), 0.01)
        self.assertEqual(M.clip_box((-3.2, 2.5, 500, 50), 100, 100), (0, 2, 100, 50))
        self.assertEqual(M.centroid(np.zeros((4, 4), bool)), None)

    def test_motion_global_change_is_compensated(self):
        prev = np.full((50, 50), 100.0, dtype=np.float32)
        cur = prev + 20.0  # 全局变亮，宠物不动
        region = np.zeros((50, 50), bool)
        region[10:30, 10:30] = True
        me = M.motion_energy(prev, cur, region)
        self.assertAlmostEqual(me["inside"], 20 / 255, places=5)
        self.assertAlmostEqual(me["activity"], 0.0, places=6)
        moved = prev.copy()
        moved[12:22, 12:22] = 250.0  # 只有区域内变化
        self.assertGreater(M.motion_energy(prev, moved, region)["activity"], 0.05)
        self.assertEqual(M.motion_energy(prev, moved, np.zeros((50, 50), bool))["activity"], 0.0)

    def test_activity_level(self):
        th = (0.01, 0.03, 0.08)
        self.assertEqual([M.activity_level(v, th) for v in (0.0, 0.02, 0.05, 0.2)],
                         ["static", "low", "medium", "high"])


class SegmentTests(unittest.TestCase):
    def test_gap_fill_and_min_length(self):
        times = [i * 0.2 for i in range(20)]
        flags = [False] * 20
        for i in (2, 3, 4, 6, 7, 15):  # 2-4 与 6-7 间隔 0.2 s → 合并；15 单点 0.2 s → 丢弃
            flags[i] = True
        segs = flags_to_segments(times, flags, dt=0.2, gap_fill=0.6, min_len=0.4)
        self.assertEqual(segs, [[0.4, 1.6]])

    def test_end_time_clips_last_segment(self):
        segs = flags_to_segments([0.0, 0.2], [True, True], dt=0.2, gap_fill=0, min_len=0, end_time=0.3)
        self.assertEqual(segs, [[0.0, 0.3]])


class ActionTests(unittest.TestCase):
    def test_load_jsonl_merge_and_review(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            lines = [
                {"t_start": 0, "t_end": 2, "label": "eating", "score": 0.9, "top5": [["eating", 0.9]]},
                {"t_start": 2, "t_end": 4, "label": "eating", "score": 0.7},
                {"t_start": 4, "t_end": 5, "label": "abnormal", "score": 0.8},
                {"t_start": 5, "t_end": 6, "label": "grooming", "score": 0.3},
                {"status": "heartbeat"},
            ]
            p.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
            segs = mark_review(merge_segments(load_timeline(p)), review_score=0.5)
        self.assertEqual([s["label"] for s in segs], ["eating", "abnormal", "grooming"])
        self.assertEqual((segs[0]["t_start"], segs[0]["t_end"]), (0.0, 4.0))
        self.assertAlmostEqual(segs[0]["score"], 0.8, places=4)
        self.assertEqual(segs[0]["n_windows"], 2)
        self.assertEqual([s["needs_cloud_review"] for s in segs], [False, True, True])
        self.assertEqual(segs[1]["review_reasons"], ["abnormal_class"])
        self.assertEqual(segs[2]["review_reasons"], ["low_confidence"])
        self.assertEqual(label_at(segs, 3.5, 4.5)["label"], "eating")  # 重叠 0.5 = 0.5，先到者
        self.assertIsNone(label_at(segs, 10, 11))

    def test_json_object_form(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.json"
            p.write_text(json.dumps({"segments": [{"start_sec": 1, "end_sec": 2, "label": "drinking"}]}))
            self.assertEqual(load_timeline(p)[0]["t_start"], 1.0)

    def test_sliding_windows_cover_without_overlap(self):
        for dur in (3.0, 10.0, 11.3):
            wins = sliding_windows(dur, 4.0, 2.0)
            self.assertAlmostEqual(wins[0][2], 0.0)
            self.assertAlmostEqual(wins[-1][3], dur)
            for a, b in zip(wins, wins[1:]):
                self.assertAlmostEqual(a[3], b[2])
            for w0, w1, _, _ in wins:
                self.assertLessEqual(w1, dur + 1e-9)


class SourceTests(unittest.TestCase):
    def test_track_json_scaling(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "track.json"
            p.write_text(json.dumps({"frames": 3, "smooth_track": [{"frame": 1, "box": [100, 50, 300, 250]}]}))
            src = TrackJsonPetSource(p)
            src.configure((2000, 1000), (1000, 500))
            self.assertEqual(src.observe(None, 0), [])
            self.assertEqual(src.observe(None, 1)[0].box, (50.0, 25.0, 150.0, 125.0))

    def test_haar_cascade_loads_when_available(self):
        if not find_cat_face_cascade():
            self.skipTest("OpenCV cat-face cascade not installed here")
        src = HaarCatFaceSource()
        self.assertEqual(src.detect(np.zeros((240, 320, 3), np.uint8), [(10, 10, 200, 200)]), [])
        self.assertEqual(src.detect(np.zeros((240, 320, 3), np.uint8), []), [])


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.video = Path(cls.tmp.name) / "synthetic.avi"
        write_synthetic_video(cls.video)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_payload(self, **kw):
        cfg = HighlightConfig(analysis_fps=5, window_sec=1.0)
        return extract_highlights(str(self.video), FakePet(), FaceByFrame(), cfg, device_id="dev-1",
                                  camera_id="cam-1", **kw)

    def test_payload_values(self):
        behavior = [{"t_start": 0.0, "t_end": 2.0, "label": "activity", "score": 0.9},
                    {"t_start": 2.0, "t_end": 4.0, "label": "abnormal", "score": 0.6}]
        p = self.run_payload(behavior=behavior, include_samples=True)
        self.assertEqual(p["schema"], SCHEMA)
        self.assertIsNone(p["cloud_judgement"])
        self.assertEqual(p["analysis"]["sample_step"], 3)
        self.assertEqual(p["analysis"]["area_source"], "box")
        s = p["summary"]
        self.assertAlmostEqual(s["duration_sec"], 4.0, places=3)
        self.assertEqual(p["segments"]["pet_visible"], [[1.0, 3.0]])
        self.assertAlmostEqual(s["pet_visible_sec"], 2.0)
        self.assertAlmostEqual(s["pet_visible_ratio"], 0.5)
        self.assertEqual(p["segments"]["body_large"], [[1.0, 3.0]])
        self.assertAlmostEqual(s["body_area_ratio"]["mean"], SQ * SQ / (W * H), places=3)
        self.assertEqual(p["segments"]["face_exposed"], [[2.0, 3.0]])
        self.assertAlmostEqual(s["face_exposed_sec"], 1.0)
        self.assertAlmostEqual(s["face_exposed_ratio_of_visible"], 0.5)
        self.assertAlmostEqual(s["face_area_ratio"]["max"], 1600 / (W * H), places=3)
        self.assertAlmostEqual(s["face_body_ratio"]["mean"], 0.25, places=3)
        self.assertGreater(s["activity"]["mean"], 0.01)  # 方块一直在动
        self.assertGreater(s["displacement"]["mean"], 0)
        self.assertAlmostEqual(s["brightness"]["min"], 30 / 255, delta=0.01)
        # 窗口：1 s 一个，共 4 个；第 0 个窗口无猫
        self.assertEqual(len(p["windows"]), 4)
        self.assertEqual(p["windows"][0]["pet_present_ratio"], 0.0)
        self.assertEqual(p["windows"][1]["pet_present_ratio"], 1.0)
        self.assertEqual(p["windows"][2]["face_exposed_ratio"], 1.0)
        self.assertEqual(p["windows"][2]["action"]["label"], "abnormal")
        # 行为：abnormal 段需云端复核
        self.assertTrue(p["behavior"]["needs_cloud_review"])
        self.assertEqual(p["behavior"]["source"], "timeline_json")
        # 亮点参考候选（design D9）：字段总在，规则与阈值记录在 analysis 里，不影响 cloud_judgement
        self.assertIsInstance(p["highlight_candidates"], list)
        self.assertEqual(p["analysis"]["highlight_rule"]["name"], RULE_NAME)
        self.assertFalse(p["analysis"]["highlight_rule"]["calibrated"])
        self.assertEqual(len(p["samples"]), 20)
        json.dumps(p)  # 可序列化

    def test_event_id_stable_and_outbox_no_overwrite(self):
        a, b = self.run_payload(), self.run_payload()
        self.assertEqual(a["event_id"], b["event_id"])
        self.assertNotEqual(a["event_id"], self.run_payload(start_time="2026-11-02T10:00:00+08:00")["event_id"])
        with tempfile.TemporaryDirectory() as d:
            path, new = write_outbox(a, d)
            self.assertTrue(new)
            first = path.read_bytes()
            b["summary"]["duration_sec"] = -1
            path2, new2 = write_outbox(b, d)
            self.assertFalse(new2)
            self.assertEqual(path2.read_bytes(), first)
            self.assertEqual(sorted(x.name for x in Path(d).iterdir()), [path.name])

    def test_no_pet_source(self):
        p = extract_highlights(str(self.video), NoPetSource(), NoFaceSource(), HighlightConfig())
        self.assertEqual(p["summary"]["pet_visible_sec"], 0.0)
        self.assertEqual(p["segments"]["face_exposed"], [])
        self.assertEqual(p["behavior"], {"source": "none", "segments": [], "needs_cloud_review": False})
        self.assertEqual(p["analysis"]["area_source"], "none")
        self.assertIsNotNone(p["summary"]["brightness"]["mean"])

    def test_cli_without_models(self):
        import extract_highlight_features as cli

        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "o" / "p.json"
            box = Path(d) / "outbox"
            rc = cli.main(["--video", str(self.video), "--pet-source", "none", "--face", "none",
                           "--out", str(out), "--outbox", str(box), "--camera-id", "cam-9"])
            self.assertEqual(rc, 0)
            p = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(p["device"]["camera_id"], "cam-9")
            self.assertTrue((box / f"{p['event_id']}.json").is_file())


def win(t: float, area=None, act=None, face=0.0, bright=0.5, action=None) -> dict:
    """合成 1 秒窗口（字段与 build_windows 一致的子集）。area=None 表示无猫。"""
    return {"t_start": float(t), "t_end": float(t + 1), "body_area_ratio_mean": area,
            "body_area_ratio_max": area or 0.0, "activity_mean": act, "face_exposed_ratio": face,
            "brightness": bright, "action": {"label": action, "score": 0.8} if action else None}


def timeline(n: int, hot: dict) -> list[dict]:
    """n 秒；hot = {秒: (area, act)}，其余秒为“有猫但小且静止”。"""
    return [win(t, *hot.get(t, (0.01, 0.005))) for t in range(n)]


class CandidateTests(unittest.TestCase):
    cfg = HighlightConfig()

    def test_large_and_active(self):
        ws = timeline(10, {t: (0.10, 0.05) for t in range(3, 7)})
        c = find_candidates(ws, 10.0, self.cfg)
        self.assertEqual(len(c), 1)
        c = c[0]
        self.assertEqual((c["t_start"], c["t_end"], c["core_start"], c["core_end"]), (2.0, 8.0, 3.0, 7.0))
        self.assertEqual((c["highlight_sec"], c["rank"]), (4.0, 1))
        self.assertAlmostEqual(c["score"], 0.5 * 0.10 / 0.15 + 0.5 * 0.05 / 0.08, places=4)
        self.assertAlmostEqual(c["body_area_ratio_mean"], 0.10)
        self.assertAlmostEqual(c["activity_mean"], 0.05)

    def test_large_static_small_active_and_no_pet_are_empty(self):
        self.assertEqual(find_candidates(timeline(10, {t: (0.20, 0.01) for t in range(10)}), 10, self.cfg), [])
        self.assertEqual(find_candidates(timeline(10, {t: (0.02, 0.20) for t in range(10)}), 10, self.cfg), [])
        self.assertEqual(find_candidates([win(t) for t in range(10)], 10, self.cfg), [])
        self.assertEqual(find_candidates([], 0, self.cfg), [])

    def test_threshold_is_inclusive(self):
        ws = timeline(6, {t: (0.05, 0.03) for t in range(1, 4)})
        self.assertEqual(len(find_candidates(ws, 6, self.cfg)), 1)

    def test_gap_merge_and_short_drop(self):
        one_gap = timeline(12, {t: (0.1, 0.05) for t in (2, 3, 5, 6)})
        c = find_candidates(one_gap, 12, self.cfg)
        self.assertEqual([(x["core_start"], x["core_end"], x["highlight_sec"]) for x in c], [(2.0, 7.0, 4.0)])
        two_gap = timeline(12, {t: (0.1, 0.05) for t in (2, 3, 6, 7)})
        self.assertEqual(len(find_candidates(two_gap, 12, self.cfg)), 2)
        single = timeline(12, {5: (0.3, 0.2)})
        self.assertEqual(find_candidates(single, 12, self.cfg), [])

    def test_padding_clipped_to_video(self):
        ws = timeline(10, {0: (0.1, 0.05), 1: (0.1, 0.05), 8: (0.1, 0.05), 9: (0.1, 0.05)})
        c = sorted(find_candidates(ws, 10.0, self.cfg), key=lambda x: x["t_start"])
        self.assertEqual([(x["t_start"], x["t_end"]) for x in c], [(0.0, 3.0), (7.0, 10.0)])

    def test_long_run_keeps_best_span_within_max(self):
        hot = {t: (0.1, 0.035) for t in range(20)}
        hot.update({t: (0.1, 0.07) for t in range(12, 20)})
        c = find_candidates(timeline(20, hot), 20.0, self.cfg)
        self.assertEqual(len(c), 1)
        self.assertLessEqual(c[0]["duration_sec"], self.cfg.highlight_max_sec + 1e-9)
        self.assertEqual((c[0]["core_start"], c[0]["core_end"]), (12.0, 20.0))
        self.assertEqual((c[0]["t_start"], c[0]["t_end"]), (11.0, 20.0))

    def test_top_k_by_score(self):
        hot = {}
        for start, act in ((0, 0.04), (5, 0.08), (10, 0.05), (15, 0.06)):
            hot.update({start: (0.1, act), start + 1: (0.1, act)})
        c = find_candidates(timeline(20, hot), 20.0, self.cfg)
        self.assertEqual([x["core_start"] for x in c], [5.0, 15.0, 10.0])
        self.assertEqual([x["rank"] for x in c], [1, 2, 3])
        cfg1 = HighlightConfig(highlight_top_k=1)
        self.assertEqual(len(find_candidates(timeline(20, hot), 20.0, cfg1)), 1)

    def test_reference_fields_and_determinism(self):
        ws = timeline(8, {t: (0.1, 0.05) for t in range(2, 5)})
        ws[2]["face_exposed_ratio"] = 0.5
        ws[3]["face_exposed_ratio"] = 1.0
        for t, label in ((2, "play"), (3, "play"), (4, "walk")):
            ws[t]["action"] = {"label": label, "score": 0.8, "needs_cloud_review": False}
        snapshot = json.dumps(ws, sort_keys=True)
        a, b = find_candidates(ws, 8.0, self.cfg), find_candidates(ws, 8.0, self.cfg)
        self.assertEqual(a, b)
        self.assertEqual(json.dumps(ws, sort_keys=True), snapshot)  # 不改输入
        self.assertAlmostEqual(a[0]["face_exposed_sec"], 1.5)
        self.assertEqual(a[0]["action"]["label"], "play")
        self.assertAlmostEqual(a[0]["brightness_mean"], 0.5)

    def test_rule_record(self):
        r = highlight_rule(HighlightConfig(highlight_area_ratio=0.04))
        self.assertEqual((r["name"], r["area_ratio"], r["activity"], r["calibrated"]), (RULE_NAME, 0.04, 0.03, False))

    def test_offline_recompute_cli(self):
        import recompute_highlight_candidates as rc

        payload = {"schema": SCHEMA, "event_id": "hl-x", "source": {"duration_sec": 10.0},
                   "summary": {"duration_sec": 10.0}, "analysis": {"config": HighlightConfig().to_dict()},
                   "windows": timeline(10, {t: (0.1, 0.05) for t in range(3, 7)}), "cloud_judgement": None}
        with tempfile.TemporaryDirectory() as d:
            src = Path(d) / "p.json"
            src.write_text(json.dumps(payload), encoding="utf-8")
            self.assertEqual(rc.main([str(src), "--out-dir", str(Path(d) / "out")]), 0)
            out = json.loads((Path(d) / "out" / "p.json").read_text(encoding="utf-8"))
            self.assertEqual(len(out["highlight_candidates"]), 1)
            self.assertTrue(out["analysis"]["highlight_rule"]["offline_recompute"])
            self.assertIsNone(out["cloud_judgement"])
            self.assertEqual(rc.main([str(src), "--highlight-area-ratio", "0.2"]), 0)  # 只打印
            with self.assertRaises(SystemExit):
                rc.main([str(src), "--out-dir", d])  # 不覆盖输入


if __name__ == "__main__":
    unittest.main()
