import unittest
from os import environ
from unittest.mock import patch

from fastapi.testclient import TestClient
from backend.app.main import app


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(environ, {"DATA_MODE": "fixture"})
        self.environment.start()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.environment.stop()

    def test_brief_discloses_synthetic_stale_data(self):
        response = self.client.get("/air/now?lat=28.61&lon=77.21")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["data_mode"], "fixture")
        self.assertTrue(body["stale"])
        self.assertEqual(body["hourly_subindex_estimate"]["value"], 323)
        self.assertEqual(body["valid_hours"], 24)

    def test_forecast_from_fixed_demo_hour(self):
        body = self.client.get("/air/forecast").json()
        self.assertEqual(body["available_hours"], 48)
        self.assertEqual(body["hours"][0]["timestamp"], "2025-11-02T00:00:00+00:00")
        self.assertEqual(body["hours"][-1]["timestamp"], "2025-11-03T23:00:00+00:00")
        self.assertEqual(body["data_mode"], "fixture")
        self.assertEqual(self.client.get("/air/forecast?hours=49").status_code, 422)

    def test_empty_live_cache_returns_503(self):
        app.state.mode = "live"
        app.state.snapshot = None
        for route in ["/air/now", "/air/forecast"]:
            self.assertEqual(self.client.get(route).status_code, 503)

    def test_indoor_scenario_and_browser_preflight(self):
        payload = {"outdoor_pm25_ug_m3": [100], "floor_area_m2": 15, "ceiling_height_m": 3}
        response = self.client.post("/simulate/indoor", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["room_volume_m3"], 45)
        self.assertEqual(self.client.post("/simulate/indoor", json={}).status_code, 422)
        headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"}
        self.assertEqual(self.client.options("/simulate/indoor", headers=headers).status_code, 200)

    def test_severe_range_in_current_average_and_forecast(self):
        series, reference = app.state.snapshot
        app.state.snapshot = ({hour: 300 for hour in series}, reference)
        current = self.client.get("/air/now").json()
        forecast = self.client.get("/air/forecast?hours=1").json()
        severe = {"band": "Severe", "value": None, "value_range": [401, 500]}
        self.assertEqual(current["hourly_subindex_estimate"], severe)
        self.assertEqual(current["pm25_subindex_24h"], severe)
        self.assertEqual(forecast["hours"][0]["subindex_estimate"], severe)

    def test_health(self):
        self.assertEqual(self.client.get("/health").json()["status"], "ok")

    def test_invalid_and_uncovered_coordinates(self):
        for query in ["lat=91", "lat=nan", "lon=inf", "lat=19&lon=73"]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(f"/air/now?{query}").status_code, 422)

    def test_cors_allow_list(self):
        allowed = self.client.get("/health", headers={"Origin": "http://localhost:5173"})
        denied = self.client.get("/health", headers={"Origin": "https://example.com"})
        self.assertEqual(allowed.headers["access-control-allow-origin"], "http://localhost:5173")
        self.assertNotIn("access-control-allow-origin", denied.headers)


class ConfigurationTests(unittest.TestCase):
    def test_unsupported_mode_fails_startup(self):
        with patch.dict(environ, {"DATA_MODE": "typo"}):
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass
