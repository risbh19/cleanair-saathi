"""Validate deployment configuration, migrate storage, then start the web server."""
import os
import re
import sys

from backend.app.web import frontend_directory
from backend.db.migrate import migrate


def configuration():
    try:
        port = int(os.getenv("PORT", "8000"))
    except ValueError:
        raise RuntimeError("PORT must be an integer between 1 and 65535") from None
    if not 1 <= port <= 65535:
        raise RuntimeError("PORT must be an integer between 1 and 65535")
    if not os.getenv("DATABASE_URL", "").strip():
        raise RuntimeError("Set DATABASE_URL to a persistent PostgreSQL database")
    if os.getenv("DATA_MODE", "fixture") not in {"fixture", "replay", "live"}:
        raise RuntimeError("DATA_MODE must be fixture, replay or live")
    mode = os.getenv("LLM_MODE", "reference")
    if mode not in {"reference", "replay", "live"}:
        raise RuntimeError("LLM_MODE must be reference, replay or live")
    if mode == "live":
        if not os.getenv("GEMINI_API_KEY", "").strip():
            raise RuntimeError("Set GEMINI_API_KEY for LLM_MODE=live")
        if not re.fullmatch(r"[a-zA-Z0-9.-]+", os.getenv("GEMINI_MODEL", "")):
            raise RuntimeError("Set GEMINI_MODEL to an available Gemini model ID")
    return port


def main():
    port = configuration()
    frontend_directory()
    try:
        migrate()
    except Exception:
        # Provider exceptions can contain hostnames, usernames or connection strings.
        raise SystemExit("Database migration failed; check database connectivity and permissions") from None
    os.execv(sys.executable, [sys.executable, "-m", "uvicorn", "backend.app.web:create_app",
                             "--factory", "--host", "0.0.0.0", "--port", str(port),
                             "--no-access-log"])


if __name__ == "__main__":
    main()
