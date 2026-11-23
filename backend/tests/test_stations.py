import asyncio
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.forecast import HOUR
from backend.app.services.stations import Observation, observation, refresh_stations, station_summary


class StationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.hour = self.now.replace(minute=0, second=0, microsecond=0)
        self.cache = {i: Observation(i, f"Station {i}", "Provider", 28.61, 77.20 + .01*i,
                                     self.now - HOUR, value)
                      for i, value in enumerate([30, 90, 20, 200], 1)}
        self.loc = {"id": 1, "name": "Delhi", "provider": {"name": "Provider"},
                    "coordinates": {"latitude": 28.61, "longitude": 77.21},
                    "sensors": [{"id": 9, "parameter": {"name": "pm25", "units": "µg/m³"}}]}
        self.row = {"locationsId": 1, "sensorsId": 9, "value": 0,
                    "datetime": {"utc": (self.now - HOUR).isoformat()}}

    def test_nearest_three_distinct_stations(self):
        summary = station_summary(self.cache, 28.61, 77.24, self.now)
        self.assertEqual(summary["value"], 90)
        self.assertEqual([s["location_id"] for s in summary["stations"]], [4, 3, 2])

    def test_validate_readings_and_freshness(self):
        self.assertEqual(observation(self.loc, self.row, {9}, self.now).value, 0)
        for change in [{"locationsId": 2}, {"sensorsId": 99}, {"value": -1}, {"value": float("nan")},
                       {"datetime": {"utc": (self.now - 3*HOUR).isoformat()}},
                       {"datetime": {"utc": (self.now + HOUR).isoformat()}}]:
            with self.subTest(change=change):
                self.assertIsNone(observation(self.loc, {**self.row, **change}, {9}, self.now))

    def test_worker_ingests_one_latest_valid_reading_per_station(self):
        mock_app = SimpleNamespace(state=SimpleNamespace(stations={}))
        def get(path, key, query):
            if path == "locations":
                return [self.loc]
            self.assertEqual(path, "locations/1/latest")
            return [self.row, {**self.row, "sensorsId": 100, "value": 999}]

        async def stop_after_pass(delay):
            if delay == 900:
                raise asyncio.CancelledError

        with patch("backend.app.services.stations.get_page", side_effect=get), \
             patch("backend.app.services.stations.asyncio.sleep", side_effect=stop_after_pass), \
             self.assertRaises(asyncio.CancelledError):
            asyncio.run(refresh_stations(mock_app, "test"))
        self.assertEqual(mock_app.state.stations[1].value, 0)

    def test_source_precedence_and_independent_history(self):
        with TestClient(app) as client, patch("backend.app.main.utc_now", return_value=self.now):
            app.state.mode = "live"
            app.state.stations = self.cache
            app.state.snapshot = ({self.hour-i*HOUR: 120 for i in range(24)}, self.now)
            result = client.get("/air/now?lat=28.61&lon=77.24").json()
            self.assertEqual(result["hourly_pm25_ug_m3"], 90)
            self.assertEqual(result["mean_24h_pm25_ug_m3"], 120)
            self.assertIn("CAMS", result["average_source"])
            app.state.snapshot = None
            result = client.get("/air/now").json()
            self.assertEqual(len(result["stations"]), 3)
            self.assertIsNone(result["mean_24h_pm25_ug_m3"])
            self.assertEqual(client.get("/air/forecast").status_code, 503)
            app.state.snapshot = ({self.hour: 120}, self.now)
            with patch("backend.app.main.utc_now", return_value=self.now + 2*HOUR):
                result = client.get("/air/now").json()
                self.assertEqual(result["stations"], [])
                self.assertEqual(result["hourly_pm25_ug_m3"], 120)
