"""CleanAir Saathi's fixture-backed first API milestone."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from os import environ
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .brief import air_brief, load_csv


FIXTURE = Path(__file__).resolve().parents[1] / "data/fixtures/synthetic_day.csv"
SOURCE_URL = "https://ies.gov.in/arthapedia/concept/national-air-quality-index"


@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = environ.get("DATA_MODE", "fixture")
    if mode != "fixture":
        raise RuntimeError("This milestone supports DATA_MODE=fixture")
    app.state.readings = load_csv(FIXTURE)
    yield


app = FastAPI(title="CleanAir Saathi", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_methods=["GET"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health():
    return {"status": "ok", "data_mode": "fixture"}


@app.get("/air/now")
def now(
    request: Request,
    lat: float = Query(28.61, ge=-90, le=90),
    lon: float = Query(77.21, ge=-180, le=180),
):
    # This fixture represents one illustrative Delhi cell.
    if not (28.5 <= lat <= 28.8 and 77.0 <= lon <= 77.4):
        raise HTTPException(422, "The synthetic Delhi fixture covers lat 28.5–28.8, lon 77.0–77.4")
    readings = request.app.state.readings
    end = max(readings)
    age = max(0, (datetime.now(timezone.utc) - end).total_seconds() / 3600)
    return {
        "source": "Synthetic demonstration series",
        "data_mode": "fixture",
        "location": {"lat": 28.61, "lon": 77.21, "locality": "Delhi"},
        "age_hours": round(age, 1),
        "stale": end < datetime.now(timezone.utc) - timedelta(hours=3),
        "methodology_url": SOURCE_URL,
        **air_brief(readings, end),
    }
