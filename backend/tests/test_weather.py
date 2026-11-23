import unittest
from datetime import datetime, timezone
from os import environ
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.weather import UNITS, parse_weather, weather_window


class WeatherTests(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "hourly_units": {"time": "unixtime", **UNITS},
            "hourly": {"time": [0, 7200], "temperature_2m": [-3, None],
                       "relative_humidity_2m": [0, 85], "wind_speed_10m": [0, 2],
                       "boundary_layer_height": [None, 400]},
        }

    def test_values_and_missing_hours(self):
        result = weather_window(parse_weather(self.payload), datetime.fromtimestamp(0, timezone.utc), 3)
        self.assertEqual(result["available_hours"], 2)
        self.assertEqual(result["hours"][0]["temperature_2m"], -3)
        self.assertIsNone(result["hours"][1]["wind_speed_10m"])
        self.assertIsNone(result["hours"][2]["temperature_2m"])

    def test_invalid_response(self):
        for key, values in [("time", [0, 1]), ("time", [0, 0]), ("relative_humidity_2m", [1, 101]),
                            ("wind_speed_10m", [False, 0]), ("temperature_2m", [1]),
                            ("boundary_layer_height", [float("nan"), 1])]:
            with self.subTest(key=key), patch.dict(self.payload["hourly"], {key: values}), self.assertRaises(ValueError):
                parse_weather(self.payload)
        with patch.dict(self.payload["hourly_units"], {"wind_speed_10m": "km/h"}), self.assertRaises(ValueError):
            parse_weather(self.payload)

    def test_fixture_alignment_and_weather_outage(self):
        with patch.dict(environ, {"DATA_MODE": "fixture"}), TestClient(app) as client:
            weather = client.get("/weather/forecast").json()
            air = client.get("/air/forecast").json()
            self.assertEqual([h["timestamp"] for h in weather["hours"]], [h["timestamp"] for h in air["hours"]])
            self.assertEqual(weather["available_hours"], 48)
            self.assertEqual(weather["data_mode"], "fixture")
            self.assertIsNone(weather["fetched_at"])
            self.assertEqual(len(client.get("/weather/forecast?hours=1").json()["hours"]), 1)
            self.assertEqual(client.get("/weather/forecast?hours=49").status_code, 422)
            app.state.weather = None
            self.assertEqual(client.get("/weather/forecast").status_code, 503)
            self.assertEqual(client.get("/air/now").status_code, 200)
