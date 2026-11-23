import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.db.migrate import connect, migrate


PROFILE = {
    "lat": 28.6139, "lon": 77.2091, "locality": "Central Delhi", "home_type": "flat",
    "room_area_m2": 12, "ceiling_m": 2.7, "windows_leaky": False, "purifier_cadr_m3h": 0,
    "cooking_fuel": "lpg", "budget_band": "low",
    "members": [{"age_band": "adult", "sensitive": False, "commutes": [
        {"mode": "metro", "distance_km": 7, "depart_time": "08:30", "return_time": "18:00"}]}]
}


def token():
    return {"Authorization": f"Bearer {uuid4()}"}


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to a disposable PostgreSQL database")
class HouseholdTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"DATABASE_URL": os.environ["TEST_DATABASE_URL"]}))
        migrate()
        self.client = self.enterContext(TestClient(app))
        self.headers = token()
        self.other = token()

    def save(self, profile, headers=None):
        result = self.client.post("/households", json=profile, headers=headers or self.headers)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_plan_uses_owned_household_and_handles_live_outage(self):
        saved = self.save(PROFILE)
        try:
            self.assertEqual(self.client.get("/plan/today").status_code, 401)
            self.assertEqual(self.client.get("/plan/today", headers=self.other).status_code, 404)
            result = self.client.get("/plan/today", headers=self.headers)
            self.assertEqual(result.headers["cache-control"], "no-store")
            self.assertEqual(result.json()["band_used"], "Very poor")
            self.assertIn("avoid_roadside_wait", [a["id"] for a in result.json()["actions"]])
            app.state.mode = "live"
            for snapshot in (app.state.snapshot, None):
                app.state.snapshot = snapshot
                fallback = self.client.get("/plan/today", headers=self.headers).json()
                self.assertIsNone(fallback["band_used"])
                self.assertNotIn("move_activity_indoors", [a["id"] for a in fallback["actions"]])
        finally:
            self.client.delete("/households/" + saved["id"], headers=self.headers)

    def test_concurrent_plan_creation_and_owned_progress(self):
        saved = self.save(PROFILE)
        self.save(PROFILE, self.other)
        def load(_):
            return self.client.get("/plan/today", headers=self.headers).json()
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.map(load, range(2))
        self.assertEqual(first, second)
        item = first["actions"][0]
        path = f"/plan/items/{item['item_id']}/status"
        def update(status, headers):
            return self.client.post(path, json={"status": status}, headers=headers)
        self.assertEqual(update("done", {}).status_code, 401)
        self.assertEqual(update("done", self.other).status_code, 404)
        self.assertEqual(update("invalid", self.headers).status_code, 422)
        for status in ["done", "done", "skipped", "planned"]:
            self.assertEqual(update(status, self.headers).json()["status"], status)
            self.assertEqual(load(0)["actions"][0]["status"], status)
        self.save({**PROFILE, "purifier_cadr_m3h": 300})
        self.assertEqual(load(0), first)
        self.client.delete("/households/" + saved["id"], headers=self.headers)
        self.assertEqual(update("done", self.headers).status_code, 404)
        with connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM plan_items WHERE id=%s", (item["item_id"],)).fetchone(), (0,))
        other = self.client.get("/households/me", headers=self.other).json()
        self.client.delete("/households/" + other["id"], headers=self.other)

    def test_new_plan_at_delhi_midnight(self):
        saved = self.save(PROFILE)
        before = datetime(2025, 11, 2, 18, 29, tzinfo=timezone.utc)
        try:
            with patch("backend.app.main.utc_now", return_value=before):
                day_one = self.client.get("/plan/today", headers=self.headers).json()
            with patch("backend.app.main.utc_now", return_value=before + timedelta(minutes=1)):
                day_two = self.client.get("/plan/today", headers=self.headers).json()
            self.assertEqual([day_one["plan_date"], day_two["plan_date"]], ["2025-11-02", "2025-11-03"])
            self.assertNotEqual(day_one["actions"][0]["item_id"], day_two["actions"][0]["item_id"])
        finally:
            self.client.delete("/households/" + saved["id"], headers=self.headers)

    def test_replace_reload_isolate_and_delete(self):
        saved = self.save(PROFILE)
        self.assertEqual((saved["lat"], saved["lon"]), (28.61, 77.21))
        self.assertEqual(self.save(PROFILE), saved)
        with TestClient(app) as returning:
            result = returning.get("/households/me", headers=self.headers)
            self.assertEqual(result.json(), saved)
            self.assertEqual(result.headers["cache-control"], "no-store")
        route = "/households/" + saved["id"]
        self.assertEqual(self.client.get("/households/me", headers=self.other).status_code, 404)
        self.assertEqual(self.client.delete(route, headers=self.other).status_code, 404)
        with connect() as db:
            home, = db.execute("SELECT home FROM households WHERE id = %s", (saved["id"],)).fetchone()
            self.assertEqual((home["lat"], home["lon"]), (28.61, 77.21))
        updated = deepcopy(PROFILE)
        updated["members"].append({"age_band": "child", "sensitive": True, "commutes": []})
        updated["members"].reverse()
        updated["members"][1]["commutes"][0]["distance_km"] = 2
        expected = self.save(updated)
        self.assertEqual(expected["id"], saved["id"])
        self.assertEqual(self.client.get("/households/me", headers=self.headers).json(), expected)
        other_id = self.save(PROFILE, self.other)["id"]
        self.assertNotEqual(other_id, saved["id"])
        self.assertEqual(self.client.delete(route, headers=self.headers).status_code, 204)
        self.assertEqual(self.client.get("/households/me", headers=self.headers).status_code, 404)
        with connect() as db:
            for table in ("members", "commutes"):
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table} WHERE household_id = %s",
                                            (saved["id"],)).fetchone(), (0,))
        self.assertEqual(self.client.get("/households/me", headers=self.other).json()["id"], other_id)
        self.client.delete("/households/" + other_id, headers=self.other)

    def test_concurrent_first_saves_are_atomic(self):
        variants = [{**PROFILE, "locality": place} for place in ("Delhi", "Central Delhi")]
        with ThreadPoolExecutor(max_workers=2) as pool:
            first, second = pool.map(self.save, variants)
        self.assertEqual(first["id"], second["id"])
        self.assertIn(self.client.get("/households/me", headers=self.headers).json(), (first, second))
        self.client.delete("/households/" + first["id"], headers=self.headers)

    def test_invalid_replacement_preserves_profile(self):
        saved = self.save(PROFILE)
        for invalid in ({"members": []}, {"lat": 30}, {"phone": "123"}, {"members": [
            {"age_band": "adult", "sensitive": False, "name": "example"}]}):
            result = self.client.post("/households", headers=self.headers, json={**PROFILE, **invalid})
            self.assertEqual(result.status_code, 422)
        self.assertEqual(self.client.get("/households/me", headers=self.headers).json(), saved)
        self.assertEqual(self.client.get("/households/me").status_code, 401)
        self.client.delete("/households/" + saved["id"], headers=self.headers)
