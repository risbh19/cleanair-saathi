"""Apply pending SQL migrations in one serialized transaction."""
import os
from pathlib import Path

import psycopg


def connect():
    return psycopg.connect(os.getenv("DATABASE_URL", ""), connect_timeout=4)


def migrate():
    with connect() as db:
        db.execute("SELECT pg_advisory_xact_lock(713446821)")
        db.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY)")
        applied = {row[0] for row in db.execute("SELECT version FROM schema_migrations")}
        for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
            if path.name not in applied:
                db.execute(path.read_text(encoding="utf-8"))
                db.execute("INSERT INTO schema_migrations VALUES (%s)", (path.name,))


if __name__ == "__main__":
    migrate()
