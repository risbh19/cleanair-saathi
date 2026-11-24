import unittest
from backend.app.morning_brief import render


class MorningBriefTests(unittest.TestCase):
    def test_preview_labels_missing_and_stale_data(self):
        data = {"data_mode": "replay", "as_of": "2025-01-01T09:00:00Z",
                "hourly_pm25_ug_m3": None, "source": "archive", "stale": True}
        result = render(data)
        for text in ["replay", "older data", "unavailable", "archive", data["as_of"]]:
            self.assertIn(text, result)
