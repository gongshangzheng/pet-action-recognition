import unittest
from scripts.prepare_gate_image_pilot import select_sources


def rows_by_date(counts):
    return [dict(video=f"{date}-{i}.mp4", date=date, household=f"h{i%2}", domain=f"d{i%3}")
            for date, count in counts.items() for i in range(count)]


class PilotSelectionTests(unittest.TestCase):
    def test_exact_quotas_no_source_or_date_leakage(self):
        rows = rows_by_date({f"2026-01-{i:02d}": 10 for i in range(1, 21)})
        result = select_sources(rows, seed=4)
        self.assertEqual({k: len(v) for k, v in result.items()}, {"train": 140, "val": 30, "test": 30})
        dates = [{r["date"] for r in v} for v in result.values()]
        self.assertFalse(dates[0] & dates[1] or dates[0] & dates[2] or dates[1] & dates[2])
        self.assertEqual(len({r["video"] for split in result.values() for r in split}), 200)
        self.assertEqual(result, select_sources(rows, seed=4))

    def test_insufficient_distinct_source_pool_fails(self):
        with self.assertRaisesRegex(ValueError, "distinct videos"):
            select_sources(rows_by_date({"2026-01-01": 199}))

    def test_single_date_cannot_leak_into_test(self):
        with self.assertRaisesRegex(ValueError, "date-disjoint"):
            select_sources(rows_by_date({"2026-01-01": 250}))


if __name__ == '__main__':
    unittest.main()
