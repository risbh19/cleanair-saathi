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
        with patch.dict(environ, {"DATA_MODE": "live"}):
            with self.assertRaises(RuntimeError):
                with TestClient(app):
                    pass
