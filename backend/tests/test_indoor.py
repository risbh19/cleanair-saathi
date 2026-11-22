import unittest

from pydantic import ValidationError

from backend.app.engine.indoor import RoomScenario, simulate


class IndoorTests(unittest.TestCase):
    def scenario(self, **kwargs):
        fields = dict(floor_area_m2=12, ceiling_height_m=2.7, outdoor_pm25_ug_m3=[220] * 8)
        return simulate(RoomScenario(**(fields | kwargs)))

    def test_bedroom_example(self):
        result = self.scenario(purifier_cadr_m3_h=300)
        self.assertAlmostEqual(result["cadr_for_target_m3_h"], 155.52)
        self.assertAlmostEqual(result["baseline_closed_no_purifier"]["inhaled_pm25_ug"], 438.0, delta=0.2)
        self.assertAlmostEqual(result["selected"]["inhaled_pm25_ug"], 38.8, delta=0.1)
        self.assertAlmostEqual(result["reduction_percent"], 91.1, delta=0.1)

    def test_open_windows_can_increase_dose(self):
        result = self.scenario(windows="open")
        self.assertAlmostEqual(result["selected"]["inhaled_pm25_ug"], 536.4, delta=0.1)
        self.assertLess(result["avoided_inhaled_pm25_ug"], 0)

    def test_zero_baseline_and_varying_hours(self):
        zero = self.scenario(outdoor_pm25_ug_m3=[0])
        self.assertIsNone(zero["reduction_percent"])
        result = self.scenario(outdoor_pm25_ug_m3=[0, 90], breathing_rate_m3_h=1)
        self.assertEqual(result["selected"]["hourly_pm25_ug_m3"][0], 0)
        self.assertAlmostEqual(result["selected"]["hourly_pm25_ug_m3"][1], 56)
        self.assertAlmostEqual(result["selected"]["inhaled_pm25_ug"], 56)
        self.assertEqual(result["avoided_inhaled_pm25_ug"], 0)

    def test_invalid_inputs(self):
        for change in [{"outdoor_pm25_ug_m3": []}, {"outdoor_pm25_ug_m3": [5] * 49},
                       {"floor_area_m2": 0}, {"purifier_cadr_m3_h": -1},
                       {"deposition_rate_h": float("nan")}, {"windows": "unknown"}]:
            with self.subTest(change=change), self.assertRaises(ValidationError):
                self.scenario(**change)
