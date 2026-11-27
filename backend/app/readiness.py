"""Check storage and schema readiness without exposing connection details."""
from pathlib import Path

import psycopg

from backend.db.migrate import connect


def database_ready():
    expected = {path.name for path in (Path(__file__).resolve().parents[1] / "db/migrations").glob("*.sql")}
    try:
        with connect() as db:
            db.execute("SET LOCAL statement_timeout = '3s'")
            applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
            return bool(expected) and expected <= applied
    except psycopg.Error:
        return False
