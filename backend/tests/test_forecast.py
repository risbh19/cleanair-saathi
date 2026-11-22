import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from backend.app.main import refresh
from backend.app.services.forecast import HOUR, forecast, parse_model


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.hour = datetime(2025, 11, 1, tzinfo=timezone.utc)
        self.payload = {
            "hourly_units": {"pm2_5": "μg/m³"},
            "hourly": {"time": [int((self.hour + i * HOUR).timestamp()) for i in range(4)],
                       "pm2_5": [30, None, 30, 80]},
        }

    def test_missing_hours_and_ties(self):
        result = forecast(parse_model(self.payload), self.hour, 4)
        self.assertEqual(result["available_hours"], 3)
        self.assertIsNone(result["hours"][1]["subindex_estimate"])
        self.assertEqual(result["lowest_hour"]["timestamp"], self.hour.isoformat())
        self.assertEqual(result["highest_hour"]["pm25_ug_m3"], 80)

    def test_bad_model_response(self):
        for values in [[30], [1, 2, -1, 3], [1, 2, False, 3]]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.payload["hourly"]["pm2_5"] = values
                parse_model(self.payload)

    def test_failed_refresh_retains_previous_live_snapshot(self):
        app = SimpleNamespace(state=SimpleNamespace(snapshot=None))
        valid = parse_model(self.payload)
        delays = []

        async def wait(seconds):
            delays.append(seconds)
            if len(delays) == 2:
                raise asyncio.CancelledError

        with patch("backend.app.main.fetch_model", side_effect=[valid, OSError()]), \
             patch("backend.app.main.utc_now", return_value=self.hour), \
             patch("backend.app.main.asyncio.sleep", new=AsyncMock(side_effect=wait)), \
             self.assertRaises(asyncio.CancelledError):
            asyncio.run(refresh(app))
        self.assertEqual(delays, [3600, 300])
        self.assertEqual(app.state.snapshot, (valid, self.hour))
