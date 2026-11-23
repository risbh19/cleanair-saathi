import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from os import environ
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import FIXTURE, app


class WinterReplayTests(unittest.TestCase):
    def test_capture_integrity_and_shared_hour_grid(self):
        directory = FIXTURE.parent / "delhi-winter-2025"
        manifest = json.loads((directory / "manifest.json").read_bytes())
        first = datetime(2025, 1, 6, tzinfo=timezone.utc)
        expected = [int((first + timedelta(hours=i)).timestamp()) for i in range(168)]
        for source in ("air", "weather"):
            raw = (directory / f"{source}.json").read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest[source]["sha256"])
            hourly = json.loads(raw)["hourly"]
            self.assertEqual(hourly["time"], expected)
            for values in hourly.values():
                self.assertEqual(len(values), 168)
                self.assertNotIn(None, values)

    def test_offline_brief_and_outlook_use_recorded_dates(self):
        directory = FIXTURE.parent / "delhi-winter-2025"
        air = json.loads((directory / "air.json").read_bytes())["hourly"]["pm2_5"]
        with patch.dict(environ, {"DATA_MODE": "replay"}), patch("backend.app.main.refresh") as refresh:
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").json()["data_mode"], "replay")
                brief = client.get("/air/now").json()
                self.assertEqual(brief["as_of"], "2025-01-10T23:00:00+00:00")
                self.assertEqual(brief["hourly_pm25_ug_m3"], air[119])
                self.assertAlmostEqual(brief["mean_24h_pm25_ug_m3"], sum(air[96:120])/24)
                self.assertEqual(brief["stations"], [])
                for path in ["/air/forecast", "/weather/forecast"]:
                    result = client.get(path).json()
                    self.assertEqual(result["available_hours"], 48)
                    self.assertEqual(result["hours"][0]["timestamp"], "2025-01-11T00:00:00+00:00")
                    self.assertEqual(result["hours"][-1]["timestamp"], "2025-01-12T23:00:00+00:00")
                    self.assertIn("start_date=2025-01-06", result["source_url"])
                    self.assertIsNone(result["fetched_at"])
                    self.assertEqual(result["retrieved_on_utc"], "2026-11-23")
                refresh.assert_not_called()
