import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.db.migrate import migrate


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to a disposable database")
class CommuteTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"DATABASE_URL": os.environ["TEST_DATABASE_URL"]}))
        migrate()
        self.client = self.enterContext(TestClient(app))
        self.trip = {"distance_km": 10, "baseline": {"mode": "petrol_hatchback_lt1000cc", "travellers": 2},
                     "alternative": {"mode": "intracity_bus"}}

    def test_occupancy_signed_difference_and_sources(self):
        result = self.client.post("/simulate/commute", json=self.trip).json()
        self.assertEqual(result["baseline"]["trip_co2_g"], 635)
        self.assertAlmostEqual(result["alternative"]["trip_co2_g"], 151.61)
        self.assertAlmostEqual(result["co2_difference_g"], 483.39)
        self.assertIsNone(result["inhaled_difference_ug"])
        for key in ("baseline", "alternative"):
            self.assertTrue(result[key]["source_url"].startswith("https://"))
            self.assertEqual(result[key]["vintage"], 2015)
        reverse = {**self.trip, "alternative": self.trip["baseline"], "baseline": self.trip["alternative"]}
        self.assertAlmostEqual(self.client.post("/simulate/commute", json=reverse).json()["co2_difference_g"], -483.39)

    def test_exposure_requires_inputs_per_leg(self):
        exposure = {"pm25_ug_m3": 100, "duration_min": 30, "breathing_m3_h": 0.6}
        self.trip["baseline"]["exposure"] = exposure
        first = self.client.post("/simulate/commute", json=self.trip).json()
        self.assertEqual(first["baseline"]["inhaled_pm25_ug"], 30)
        self.assertIsNone(first["inhaled_difference_ug"])
        self.trip["alternative"]["exposure"] = {**exposure, "pm25_ug_m3": 50}
        self.assertEqual(self.client.post("/simulate/commute", json=self.trip).json()["inhaled_difference_ug"], 15)

    def test_invalid_or_unsupported_inputs(self):
        for change in [{"distance_km": 0}, {"baseline": {"mode": "metro"}},
                       {"baseline": {"mode": "scooter_lt110cc", "travellers": 3}},
                       {"alternative": {"mode": "intracity_bus", "travellers": 2}}]:
            self.assertEqual(self.client.post("/simulate/commute", json={**self.trip, **change}).status_code, 422)
