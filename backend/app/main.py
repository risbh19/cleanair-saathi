"""Cached Delhi air brief and hourly forecast."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import logging
from os import environ
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .grap import router as grap_router
from .engine.actions import daily_actions
from .households import reload_profile
from .households import router as households_router
from .services.aqi import pm25_subindex
from .services.stations import refresh_stations, station_summary
from .services.weather import fetch_weather, parse_weather, weather_window
from .engine.indoor import RoomScenario, simulate
from .brief import air_brief, load_csv
from .services.forecast import HOUR, fetch_model, forecast, parse_model

FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic_day.csv"
SOURCE_URL = "https://airquality.cpcb.gov.in/ccr_docs/About_AQI.pdf"


def utc_now():
    return datetime.now(timezone.utc)


async def refresh(app, *, weather=False):
    fetch = fetch_weather if weather else fetch_model
    while True:
        try:
            series = await asyncio.to_thread(fetch)
            fetched = utc_now()
            current = fetched.replace(minute=0, second=0, microsecond=0)
            if current not in series or not any(hour > current for hour in series):
                raise ValueError("missing current or future model hours")
            if weather:
                app.state.weather = (series, fetched)
            else:
                app.state.snapshot = (series, fetched)
            delay = 3600
        except (OSError, ValueError, KeyError, TypeError, OverflowError) as exc:
            logging.getLogger(__name__).warning("%s refresh failed: %s", "Delhi weather" if weather else "Delhi air", type(exc).__name__)
            delay = 300
        await asyncio.sleep(delay)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = environ.get("DATA_MODE", "fixture")
    app.state.mode = mode
    app.state.snapshot = None
    app.state.weather = None
    app.state.stations = {}
    if mode == "fixture":
        observations = load_csv(FIXTURE)
        end = max(observations)
        observations.update(load_csv(FIXTURE.with_name("synthetic_forecast.csv")))
        app.state.snapshot = (observations, end)
        weather = parse_weather(json.loads(FIXTURE.with_name("synthetic_weather.json").read_text(encoding="utf-8")))
        app.state.weather = (weather, end)
        yield
    elif mode == "replay":
        folder = FIXTURE.parent / "delhi-winter-2025"
        def read(name):
            return json.loads((folder / name).read_text(encoding="utf-8"))
        app.state.archive = read("manifest.json")
        reference = datetime.fromisoformat(app.state.archive["as_of"])
        app.state.snapshot = (parse_model(read("air.json")), reference)
        app.state.weather = (parse_weather(read("weather.json")), reference)
        yield
    elif mode == "live":
        tasks = [asyncio.create_task(refresh(app)), asyncio.create_task(refresh(app, weather=True))]
        if key := environ.get("OPENAQ_API_KEY"):
            tasks.append(asyncio.create_task(refresh_stations(app, key)))
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
    else:
        raise RuntimeError("DATA_MODE must be fixture, replay or live")


app = FastAPI(title="CleanAir Saathi", version="0.2.0", lifespan=lifespan)
app.include_router(households_router)
app.include_router(grap_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "data_mode": request.app.state.mode}


def delhi_coordinates(lat: float = Query(28.61, ge=-90, le=90),
               lon: float = Query(77.21, ge=-180, le=180)):
    if not (28.5 <= lat <= 28.8 and 77.0 <= lon <= 77.4):
        raise HTTPException(422, "This feed covers the Delhi cell only")
    return lat, lon


def cached_air(request: Request):
    snapshot = request.app.state.snapshot
    if snapshot is None:
        raise HTTPException(503, "Delhi air data is still unavailable", headers={"Retry-After": "60"})
    series, fetched = snapshot
    demo = request.app.state.mode == "fixture"
    now = utc_now()
    hour = fetched if request.app.state.mode != "live" else now.replace(minute=0, second=0, microsecond=0)
    metadata = {
        "source": "Synthetic demonstration series" if demo else "CAMS via Open-Meteo (regional model)",
        "source_url": None if demo else "https://open-meteo.com/en/docs/air-quality-api",
        "data_mode": request.app.state.mode,
        "location": {"lat": 28.61, "lon": 77.21, "locality": "Delhi"},
        "fetched_at": None if demo else fetched.isoformat(),
        "stale": now - fetched >= 3 * HOUR,
        "methodology_url": SOURCE_URL,
    }
    if request.app.state.mode == "replay":
        archive = request.app.state.archive
        metadata.update(source=archive["air"]["source"], source_url=archive["air"]["url"],
                        retrieved_on_utc=archive["retrieved_on_utc"], fetched_at=None)
    return series, hour, metadata, now


@app.get("/air/now")
def now(request: Request, coords=Depends(delhi_coordinates)):
    requested = utc_now()
    station = (station_summary(request.app.state.stations.copy(), *coords, requested)
               if request.app.state.mode == "live" else None)
    if request.app.state.snapshot is not None:
        series, hour, metadata, requested = cached_air(request)
        end = max((stamp for stamp in series if stamp <= hour), default=None)
    else:
        end = None
    if end is None and station is None:
        raise HTTPException(503, "Current Delhi air data is unavailable", headers={"Retry-After": "60"})
    if end is not None:
        age = (requested - end).total_seconds() / 3600
        brief = {**metadata, **air_brief(series, end), "age_hours": round(max(0, age), 1),
                 "stale": metadata["stale"] or age >= 3}
    else:
        brief = {"mean_24h_pm25_ug_m3": None, "pm25_subindex_24h": None, "valid_hours": 0}
    brief["average_source"] = brief.get("source")
    brief["average_as_of"] = end.isoformat() if end else None
    brief["average_stale"] = brief.get("stale")
    if station:
        stamp = station["oldest"]
        return {**brief, "source": "OpenAQ station median", "source_url": "https://openaq.org/",
                "data_mode": "live", "methodology_url": SOURCE_URL, "stale": False,
                "location": {"lat": coords[0], "lon": coords[1], "locality": "Delhi"},
                "as_of": stamp.isoformat(), "fetched_at": None,
                "age_hours": round((requested - stamp).total_seconds() / 3600, 1),
                "hourly_pm25_ug_m3": station["value"],
                "hourly_subindex_estimate": asdict(pm25_subindex(station["value"])),
                "stations": station["stations"]}
    return {**brief, "stations": []}


@app.get("/air/forecast", dependencies=[Depends(delhi_coordinates)])
def hourly_forecast(hours: int = Query(48, ge=1, le=48), context=Depends(cached_air)):
    series, hour, metadata, _ = context
    result = forecast(series, hour + HOUR, hours)
    if result["available_hours"] == 0:
        raise HTTPException(503, "No forecast hours are available for this window")
    return {**metadata, "as_of": hour.isoformat(), **result}


@app.post("/simulate/indoor")
def indoor(room: RoomScenario):
    return simulate(room)


@app.get("/weather/forecast")
def hourly_weather(request: Request, hours: int = Query(48, ge=1, le=48)):
    snapshot = request.app.state.weather
    if snapshot is None:
        raise HTTPException(503, "Delhi weather is unavailable", headers={"Retry-After": "60"})
    series, fetched = snapshot
    fixture = request.app.state.mode == "fixture"
    now = utc_now()
    hour = fetched if request.app.state.mode != "live" else now.replace(minute=0, second=0, microsecond=0)
    result = weather_window(series, hour + HOUR, hours)
    if not result["available_hours"]:
        raise HTTPException(503, "No weather forecast hours available")
    response = {**result, "as_of": hour.isoformat(), "data_mode": request.app.state.mode,
            "location": {"lat": 28.61, "lon": 77.21, "locality": "Delhi"},
            "source": "Synthetic demonstration series" if fixture else "Open-Meteo Weather Forecast",
            "source_url": None if fixture else "https://open-meteo.com/en/docs",
            "fetched_at": None if fixture else fetched.isoformat(), "stale": now - fetched >= 3 * HOUR}
    if request.app.state.mode == "replay":
        archive = request.app.state.archive
        response.update(source=archive["weather"]["source"], source_url=archive["weather"]["url"],
                        retrieved_on_utc=archive["retrieved_on_utc"], fetched_at=None)
    return response


@app.get("/plan/today")
def today_plan(request: Request, response: Response, profile=Depends(reload_profile)):
    response.headers["Cache-Control"] = "no-store"
    mode = request.app.state.mode
    try:
        brief = now(request, (profile["lat"], profile["lon"]))
    except HTTPException as exc:
        if exc.status_code != 503:
            raise
        brief = None
    band = None
    if brief and (mode != "live" or not brief["stale"]):
        estimate = brief["hourly_subindex_estimate"]
        if estimate:
            band = estimate["band"]
    return {"data_mode": mode, "band_used": band, "as_of": brief["as_of"] if brief else None,
            "actions": daily_actions(profile, band)}
