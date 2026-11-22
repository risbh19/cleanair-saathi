import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.app.brief import air_brief, load_csv
from backend.app.services.aqi import SubIndex, pm25_subindex


class SubIndexTests(unittest.TestCase):
    def test_published_examples(self):
        for value, index in [(31, 51), (45, 75), (150, 323)]:
            with self.subTest(value=value):
                self.assertEqual(pm25_subindex(value).value, index)

    def test_band_boundaries(self):
        for value, index, band in [
            (0, 0, "Good"), (30, 50, "Good"), (30.01, 51, "Satisfactory"),
            (60, 100, "Satisfactory"), (60.01, 101, "Moderately polluted"),
            (90, 200, "Moderately polluted"), (90.01, 201, "Poor"),
            (120, 300, "Poor"), (120.01, 301, "Very poor"),
            (250, 400, "Very poor"), (250.01, None, "Severe"),
        ]:
            with self.subTest(value=value):
                self.assertEqual(pm25_subindex(value), SubIndex(band, index))

    def test_invalid_concentration(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                pm25_subindex(value)


class BriefTests(unittest.TestCase):
    end = datetime(2025, 11, 1, 23, tzinfo=timezone.utc)

    def test_minimum_coverage_excludes_old_and_future(self):
        series = {self.end - timedelta(hours=i): 45 for i in range(16)}
        series[self.end - timedelta(hours=24)] = 1000
        series[self.end + timedelta(hours=1)] = 1000
        brief = air_brief(series, self.end)
        self.assertEqual(brief["valid_hours"], 16)
        self.assertEqual(brief["pm25_subindex_24h"]["value"], 75)
        del series[self.end]
        brief = air_brief(series, self.end)
        self.assertIsNone(brief["pm25_subindex_24h"])
        self.assertIsNone(brief["hourly_subindex_estimate"])

    def test_current_and_average_are_distinct(self):
        series = {self.end - timedelta(hours=i): 0 for i in range(24)}
        series[self.end] = 240
        brief = air_brief(series, self.end)
        self.assertEqual(brief["mean_24h_pm25_ug_m3"], 10)
        self.assertEqual(brief["hourly_subindex_estimate"]["band"], "Very poor")
        self.assertEqual(brief["pm25_subindex_24h"]["band"], "Good")

    def test_csv_duplicate_offset_and_bad_timestamp(self):
        for stamp in ["2025-11-01T05:30:00+05:30", "2025-11-01T01:01:00Z", "2025-11-01T01:00:00"]:
            with self.subTest(stamp=stamp), tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "air.csv"
                path.write_text(f"timestamp,pm25_ug_m3\n2025-11-01T00:00:00Z,45\n{stamp},55\n")
                with self.assertRaises(ValueError):
                    load_csv(path)
