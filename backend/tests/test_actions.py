import unittest

from backend.app.engine.actions import CATALOGUE, daily_actions


class ActionTests(unittest.TestCase):
    def test_catalogue_ids_translations_and_applicability(self):
        ids = [item["id"] for item in CATALOGUE]
        self.assertEqual(len(set(ids)), len(ids))
        for item in CATALOGUE:
            for lang in ("en", "hi"):
                self.assertTrue(item[lang]["step"])
                self.assertTrue(item[lang]["title"])
        profile = {"purifier_cadr_m3h": 0, "cooking_fuel": "electric",
                   "members": [{"age_band": "adult", "sensitive": False, "commutes": []}]}
        for band in (None, "Good", "Satisfactory", "Moderately polluted", "Poor", "Very poor", "Severe"):
            actions = daily_actions(profile, band)
            chosen = [a["id"] for a in actions]
            self.assertTrue(5 <= len(actions) <= 7)
            self.assertNotIn("check_purifier", chosen)
            self.assertNotIn("compare_motor_trip", chosen)
            self.assertEqual("move_activity_indoors" in chosen, band in {"Very poor", "Severe"})

    def test_profile_priority_is_repeatable(self):
        profile = {"purifier_cadr_m3h": 100, "cooking_fuel": "biomass",
                   "members": [{"age_band": "child", "sensitive": True, "commutes": [{"mode": "car"}]}]}
        actions = daily_actions(profile, "Severe")
        self.assertEqual(actions, daily_actions(profile, "Severe"))
        self.assertEqual(len(actions), 7)
        ids = [a["id"] for a in actions]
        for expected in ("review_sensitive_member_trip", "review_school_trip", "skip_biomass",
                         "check_purifier", "compare_motor_trip"):
            self.assertIn(expected, ids)
