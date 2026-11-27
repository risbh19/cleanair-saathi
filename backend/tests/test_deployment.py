import asyncio
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import psycopg

from backend.app.readiness import database_ready
from backend.app.request_limits import RequestLimits
from backend.app.web import create_app
from backend.serve import configuration, main


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"DATA_MODE": "fixture", "LLM_MODE": "reference"}))
        self.directory = directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        (directory / "assets").mkdir()
        (directory / "index.html").write_text("<html>Dashboard</html>")
        (directory / "sw.js").write_text("// worker")
        (directory / "assets/app-test.js").write_text("// application")
        self.client = self.enterContext(TestClient(create_app(directory)))

    def test_dashboard_assets_and_api_share_an_origin(self):
        shell = self.client.get("/")
        self.assertEqual(shell.status_code, 200)
        self.assertIn("Dashboard", shell.text)
        self.assertEqual(shell.headers["cache-control"], "no-cache")
        self.assertEqual(self.client.get("/sw.js").headers["cache-control"], "no-cache")
        self.assertIn("immutable", self.client.get("/assets/app-test.js").headers["cache-control"])
        self.assertEqual(self.client.get("/assets/missing.js").status_code, 404)
        self.assertEqual(self.client.get("/.env").status_code, 404)
        self.assertEqual(self.client.get("/api/air/forecast").json()["available_hours"], 48)
        self.assertEqual(self.client.get("/api/households/me").status_code, 401)
        self.assertEqual(self.client.get("/api/not-a-route").status_code, 404)
        self.assertEqual(self.client.get("/api/docs").status_code, 200)
        self.assertIn("/api", [s["url"] for s in self.client.get("/api/openapi.json").json()["servers"]])

    def test_health_does_not_hide_storage_outages(self):
        for ready, status in [(True, 200), (False, 503)]:
            with self.subTest(ready=ready), patch("backend.app.web.database_ready", return_value=ready):
                response = self.client.get("/health/ready")
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers["cache-control"], "no-store")
                self.assertEqual(self.client.get("/health").json(), {"status": "ok", "data_mode": "fixture"})

    def test_live_cache_lifecycle_starts_and_stops_on_outer_app(self):
        with patch.dict(os.environ, {"DATA_MODE": "live"}), patch("backend.app.main.refresh") as refresh:
            # Keep the asynchronous worker pending until application shutdown.
            async def pending(*args, **kwargs):
                await asyncio.Event().wait()
            refresh.side_effect = pending
            with TestClient(create_app(self.directory)) as live:
                self.assertEqual(live.get("/health").json()["data_mode"], "live")
                self.assertEqual(live.get("/api/air/forecast").status_code, 503)
            self.assertEqual(refresh.call_count, 2)

    def test_mounted_api_keeps_request_limits(self):
        with patch("backend.app.request_limits.limits", RequestLimits(maximum=1)):
            self.assertEqual(self.client.get("/api/plan/today").status_code, 401)
            response = self.client.get("/api/plan/today")
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response.headers["retry-after"], "60")


class ReadinessTests(unittest.TestCase):
    def test_database_and_migrations_are_required(self):
        versions = [(p.name,) for p in Path("backend/db/migrations").glob("*.sql")]
        db = MagicMock()
        db.__enter__.return_value = db
        with patch("backend.app.readiness.connect", return_value=db):
            for applied, expected in [(versions, True), (versions[:-1], False), ([], False)]:
                db.execute.return_value = applied
                self.assertEqual(database_ready(), expected)
        for error in [psycopg.OperationalError("private connection details"), psycopg.errors.UndefinedTable()]:
            with patch("backend.app.readiness.connect", side_effect=error):
                self.assertFalse(database_ready())


class StartupTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch.dict(os.environ, {"DATABASE_URL": "postgresql://test/db",
                          "DATA_MODE": "fixture", "LLM_MODE": "reference", "PORT": "10000"}, clear=True))

    def test_platform_port_and_live_credentials_are_validated(self):
        self.assertEqual(configuration(), 10000)
        for value in ["0", "65536", "not-a-port"]:
            with self.subTest(port=value), patch.dict(os.environ, {"PORT": value}), self.assertRaises(RuntimeError):
                configuration()
        for changes in [{"DATABASE_URL": ""}, {"DATA_MODE": "typo"}, {"LLM_MODE": "typo"},
                        {"LLM_MODE": "live", "GEMINI_API_KEY": ""},
                        {"LLM_MODE": "live", "GEMINI_API_KEY": "test", "GEMINI_MODEL": ""}]:
            with self.subTest(changes=changes), patch.dict(os.environ, changes), self.assertRaises(RuntimeError):
                configuration()

    def test_failed_migration_never_launches_server_or_reveals_connection(self):
        with patch("backend.serve.frontend_directory"), patch("backend.serve.migrate", side_effect=psycopg.OperationalError("secret-url")), patch("os.execv") as execute:
            with self.assertRaises(SystemExit) as error:
                main()
            self.assertNotIn("secret-url", str(error.exception))
            execute.assert_not_called()
