import os
import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo

from backend.app.main import app
from backend.db.migrate import connect, migrate


ORDER = {"stage": 2, "effective_from": "2025-11-01T08:00:00+05:30",
         "source_url": "https://caqm.nic.in/WriteReadData/LINKS/test-order.pdf"}
AUTH = {"Authorization": "Bearer test-admin"}


class AdminTests(unittest.TestCase):
    def test_disabled_and_invalid_credentials(self):
        with TestClient(app) as client, patch.dict(os.environ, {"GRAP_ADMIN_TOKEN": ""}):
            self.assertEqual(client.put("/admin/grap-status", json=ORDER, headers=AUTH).status_code, 503)
            with patch.dict(os.environ, {"GRAP_ADMIN_TOKEN": "test-admin"}):
                for headers in [{}, {"Authorization": "Bearer other"}]:
                    self.assertEqual(client.put("/admin/grap-status", json=ORDER, headers=headers).status_code, 401)

    def test_reject_invalid_orders_before_writing(self):
        with TestClient(app) as client, patch.dict(os.environ, {"GRAP_ADMIN_TOKEN": "test-admin"}):
            for change in [{"stage": 5}, {"stage": True}, {"effective_from": "2025-11-01T08:00"},
                           {"source_url": "http://caqm.nic.in/order.pdf"},
                           {"source_url": "https://caqm.nic.in.example.com/order.pdf"},
                           {"source_url": "https://caqm.nic.in/"}]:
                with self.subTest(change=change):
                    self.assertEqual(client.put("/admin/grap-status", json={**ORDER, **change},
                                                headers=AUTH).status_code, 422)


@unittest.skipUnless(os.getenv("TEST_DATABASE_URL"), "Set TEST_DATABASE_URL to a disposable database")
class OrderHistoryTests(unittest.TestCase):
    def test_empty_scheduled_effective_corrected_and_revoked(self):
        schema = "grap_test_" + uuid4().hex
        url = os.environ["TEST_DATABASE_URL"]
        with patch.dict(os.environ, {"DATABASE_URL": url}), connect() as db:
            db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            db.commit()
            try:
                with patch.dict(os.environ, {"DATABASE_URL": make_conninfo(url, options="-c search_path="+schema),
                                             "GRAP_ADMIN_TOKEN": "test-admin"}), TestClient(app) as client:
                    migrate()
                    def put(**changes):
                        res = client.put("/admin/grap-status", json={**ORDER, **changes}, headers=AUTH)
                        self.assertEqual(res.status_code, 200, res.text)
                        return res.json()
                    def current():
                        res = client.get("/grap/status")
                        self.assertEqual(res.status_code, 200, res.text)
                        return res.json()["order"]
                    self.assertIsNone(current())
                    put(effective_from="2100-01-01T00:00:00Z")
                    self.assertIsNone(current())
                    original = put()
                    self.assertEqual(put(), original)
                    put(effective_from="2020-01-01T00:00:00Z")
                    self.assertEqual(current(), original)
                    corrected = put(stage=3)
                    self.assertEqual(current(), corrected)
                    put(stage=0, effective_from="2025-11-02T00:00:00Z")
                    self.assertEqual(current()["stage"], 0)
            finally:
                db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
