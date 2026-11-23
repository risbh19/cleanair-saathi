"""OpenAQ v3 observations for fixed Delhi PM2.5 stations."""
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
from math import asin, cos, isfinite, radians, sin, sqrt
from statistics import median
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

MAX_AGE = timedelta(hours=3)
BASE = "https://api.openaq.org/v3"
LIMIT = 100
INVALID = (KeyError, TypeError, ValueError, OverflowError, AttributeError)


def get_page(path, key, query):
    request = Request(f"{BASE}/{path}?{urlencode(query)}", headers={"X-API-Key": key})
    with urlopen(request, timeout=10) as response:
        return json.load(response)["results"]


async def pages(path, key, **params):
    page = 1
    while True:
        rows = await asyncio.to_thread(get_page, path, key, {**params, "limit": LIMIT, "page": page})
        if not isinstance(rows, list):
            raise ValueError("invalid OpenAQ results")
        for row in rows:
            yield row
        if len(rows) < LIMIT:
            return
        page += 1
        await asyncio.sleep(1.2)


@dataclass(frozen=True)
class Observation:
    station_id: int
    name: str
    provider: str
    lat: float
    lon: float
    stamp: datetime
    value: float


def observation(location, row, sensors, now):
    try:
        stamp = datetime.fromisoformat(row["datetime"]["utc"])
        lat, lon = (location["coordinates"][k] for k in ("latitude", "longitude"))
        value = row["value"]
        if (row["locationsId"] != location["id"] or row["sensorsId"] not in sensors
                or type(value) not in (float, int) or not isfinite(value) or value < 0
                or not 28.5 <= lat <= 28.8 or not 77 <= lon <= 77.4
                or not timedelta(0) <= now - stamp < MAX_AGE):
            return None
        return Observation(location["id"], location["name"], location["provider"]["name"],
                           lat, lon, stamp, value)
    except INVALID:
        return None


async def refresh_stations(app, key):
    while True:
        delay = 900
        try:
            async for loc in pages("locations", key, bbox="77,28.5,77.4,28.8", parameters_id=2,
                                   mobile="false", iso="IN"):
                try:
                    station_id = loc["id"]
                    if type(station_id) is not int or loc.get("isMobile"):
                        continue
                    sensors = {s["id"] for s in loc["sensors"] if s["parameter"]["name"] == "pm25"
                               and s["parameter"]["units"] in ("µg/m³", "μg/m³")}
                    if not sensors:
                        continue
                    await asyncio.sleep(1.2)
                    now = datetime.now(timezone.utc)
                    latest = None
                    async for row in pages(f"locations/{station_id}/latest", key):
                        item = observation(loc, row, sensors, now)
                        if item and (latest is None or item.stamp > latest.stamp):
                            latest = item
                    if latest:
                        previous = app.state.stations.get(station_id)
                        if previous is None or latest.stamp >= previous.stamp:
                            app.state.stations[station_id] = latest
                except HTTPError as exc:
                    if exc.code != 404:
                        raise
                except INVALID:
                    continue
        except (OSError, *INVALID) as exc:
            logging.getLogger(__name__).warning("OpenAQ refresh failed: %s", type(exc).__name__)
            delay = 300
        cutoff = datetime.now(timezone.utc) - MAX_AGE
        app.state.stations = {k: v for k, v in app.state.stations.items() if v.stamp > cutoff}
        await asyncio.sleep(delay)


def station_summary(cache, lat, lon, now):
    def distance(station):
        a = sin(radians(station.lat - lat) / 2) ** 2
        a += cos(radians(lat)) * cos(radians(station.lat)) * sin(radians(station.lon - lon) / 2) ** 2
        return 12742 * asin(sqrt(a))

    nearby = sorted((distance(s), s.station_id, s) for s in cache.values()
                    if timedelta(0) <= now - s.stamp < MAX_AGE)[:3]
    if not nearby:
        return None
    return {
        "value": median(s.value for _, _, s in nearby),
        "oldest": min(s.stamp for _, _, s in nearby),
        "stations": [{"location_id": s.station_id, "name": s.name, "provider": s.provider,
                      "as_of": s.stamp.isoformat(), "pm25_ug_m3": s.value, "distance_km": round(d, 2),
                      "url": f"https://explore.openaq.org/locations/{s.station_id}"}
                     for d, _, s in nearby],
    }
