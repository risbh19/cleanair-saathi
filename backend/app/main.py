"""Cached Delhi air brief and hourly forecast."""

import asyncio
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
import logging
from os import environ
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .engine.indoor import RoomScenario, simulate
from .brief import air_brief, load_csv
from .services.forecast import HOUR, fetch_model, forecast

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic_day.csv"
SOURCE_URL = "https://ies.gov.in/arthapedia/concept/national-air-quality-index"


def utc_now():
    return datetime.now(timezone.utc)


async def refresh(app):
    while True:
        try:
            series = await asyncio.to_thread(fetch_model)
            fetched = utc_now()
            current = fetched.replace(minute=0, second=0, microsecond=0)
            if current not in series or not any(hour > current for hour in series):
                raise ValueError("missing current or future model hours")
            app.state.snapshot = (series, fetched)
            delay = 3600
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            logging.getLogger(__name__).warning("Delhi model refresh failed: %s", type(exc).__name__)
            delay = 300
        await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = environ.get("DATA_MODE", "fixture")
    app.state.mode = mode
    app.state.snapshot = None
    if mode == "fixture":
        observations = load_csv(FIXTURE)
        end = max(observations)
        observations.update(load_csv(FIXTURE.with_name("synthetic_forecast.csv")))
        app.state.snapshot = (observations, end)
        yield
    elif mode == "live":
        task = asyncio.create_task(refresh(app))
        try:
            yield
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    else:
        raise RuntimeError("DATA_MODE must be fixture or live")


app = FastAPI(title="CleanAir Saathi", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "data_mode": request.app.state.mode}


def cached_air(request: Request, lat: float = Query(28.61, ge=-90, le=90),
               lon: float = Query(77.21, ge=-180, le=180)):
    if not (28.5 <= lat <= 28.8 and 77.0 <= lon <= 77.4):
        raise HTTPException(422, "This feed covers the Delhi cell only")
    snapshot = request.app.state.snapshot
    if snapshot is None:
        raise HTTPException(503, "Delhi air data is still unavailable", headers={"Retry-After": "60"})
    series, fetched = snapshot
    demo = request.app.state.mode == "fixture"
    now = utc_now()
    hour = fetched if demo else now.replace(minute=0, second=0, microsecond=0)
    metadata = {
        "source": "Synthetic demonstration series" if demo else "CAMS via Open-Meteo (regional model)",
        "source_url": None if demo else "https://open-meteo.com/en/docs/air-quality-api",
        "data_mode": request.app.state.mode,
        "location": {"lat": 28.61, "lon": 77.21, "locality": "Delhi"},
        "fetched_at": None if demo else fetched.isoformat(),
        "stale": now - fetched >= 3 * HOUR,
        "methodology_url": SOURCE_URL,
    }
    return series, hour, metadata, now


@app.get("/air/now")
def now(context=Depends(cached_air)):
    series, hour, metadata, requested = context
    end = max((stamp for stamp in series if stamp <= hour), default=None)
    if end is None:
        raise HTTPException(503, "Current Delhi air data is unavailable")
    age = max(0, (requested - end).total_seconds() / 3600)
    return {**metadata, "stale": metadata["stale"] or age >= 3,
            "age_hours": round(age, 1), **air_brief(series, end)}


@app.get("/air/forecast")
def hourly_forecast(hours: int = Query(48, ge=1, le=48), context=Depends(cached_air)):
    series, hour, metadata, _ = context
    result = forecast(series, hour + HOUR, hours)
    if result["available_hours"] == 0:
        raise HTTPException(503, "No forecast hours are available for this window")
    return {**metadata, "as_of": hour.isoformat(), **result}


@app.post("/simulate/indoor")
def indoor(room: RoomScenario):
    return simulate(room)
