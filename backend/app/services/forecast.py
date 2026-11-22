"""Hourly Delhi PM2.5 forecasts from the regional CAMS model."""

from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import math
from urllib.request import urlopen

from .aqi import pm25_subindex

HOUR = timedelta(hours=1)
FEED = (
    "https://air-quality-api.open-meteo.com/v1/air-quality"
    "?latitude=28.61&longitude=77.21&hourly=pm2_5&past_days=1"
    "&forecast_days=4&timeformat=unixtime&timezone=GMT"
)


def parse_model(payload: dict) -> dict[datetime, float]:
    if payload["hourly_units"]["pm2_5"] != "μg/m³" and payload["hourly_units"]["pm2_5"] != "µg/m³":
        raise ValueError("unexpected PM2.5 unit")
    series = {}
    previous = None
    for stamp, value in zip(payload["hourly"]["time"], payload["hourly"]["pm2_5"], strict=True):
        if type(stamp) is not int or stamp % 3600 or (previous is not None and stamp <= previous):
            raise ValueError("expected ordered UTC hours")
        previous = stamp
        if value is None:
            continue
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("invalid concentration")
        series[datetime.fromtimestamp(stamp, timezone.utc)] = value
    return series


def fetch_model() -> dict[datetime, float]:
    with urlopen(FEED, timeout=12) as response:
        return parse_model(json.load(response))


def forecast(series: dict[datetime, float], start: datetime, hours: int) -> dict:
    rows = []
    for offset in range(hours):
        hour = start + offset * HOUR
        value = series.get(hour)
        rows.append({
            "timestamp": hour.isoformat(),
            "pm25_ug_m3": value,
            "subindex_estimate": asdict(pm25_subindex(value)) if value is not None else None,
        })
    available = [row for row in rows if row["pm25_ug_m3"] is not None]
    return {
        "hours": rows,
        "available_hours": len(available),
        "lowest_hour": min(available, key=lambda row: row["pm25_ug_m3"], default=None),
        "highest_hour": max(available, key=lambda row: row["pm25_ug_m3"], default=None),
    }
