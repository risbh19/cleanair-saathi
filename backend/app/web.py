"""Serve the production dashboard and API from one origin."""
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .main import app as api
from .readiness import database_ready


def frontend_directory():
    directory = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if not (directory / "index.html").is_file():
        raise RuntimeError("Build the dashboard first: cd frontend && npm ci && npm run build")
    return directory


class DashboardFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        # Revalidate the shell and worker so a redeploy can install new assets.
        if path in {".", "index.html", "sw.js", "manifest.webmanifest"}:
            response.headers["Cache-Control"] = "no-cache"
        elif path.startswith("assets/"):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def create_app(directory=None):
    directory = Path(directory) if directory is not None else frontend_directory()

    @asynccontextmanager
    async def lifespan(app):
        # ASGI mounts do not run the mounted application's lifespan themselves.
        async with api.router.lifespan_context(api):
            yield

    async def health(request):
        return JSONResponse({"status": "ok", "data_mode": api.state.mode},
                            headers={"Cache-Control": "no-store"})

    async def ready(request):
        available = await run_in_threadpool(database_ready)
        return JSONResponse({"status": "ready" if available else "unavailable"},
                            status_code=200 if available else 503,
                            headers={"Cache-Control": "no-store"})

    return Starlette(lifespan=lifespan, routes=[
        Route("/health", health),
        Route("/health/ready", ready),
        Mount("/api", api),
        Mount("/", DashboardFiles(directory=directory, html=True)),
    ])
