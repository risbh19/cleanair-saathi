"""Hourly modelled weather for the Delhi forecast cell."""
import json
import math
from datetime import datetime, timezone
from urllib.request import urlopen

from .forecast import HOUR

UNITS = {"temperature_2m": "°C", "relative_humidity_2m": "%",
         "wind_speed_10m": "m/s", "boundary_layer_height": "m"}
FEED = ("https://api.open-meteo.com/v1/forecast?latitude=28.61&longitude=77.21"
        "&hourly=" + ",".join(UNITS) + "&wind_speed_unit=ms&timeformat=unixtime&forecast_days=4")


def parse_weather(payload):
    hourly = payload["hourly"]
    units = payload["hourly_units"]
    if units.get("time") != "unixtime" or any(units.get(k) != v for k, v in UNITS.items()):
        raise ValueError("unexpected weather units")
    series = {}
    previous = None
    for stamp, *values in zip(hourly["time"], *(hourly[k] for k in UNITS), strict=True):
        if type(stamp) is not int or stamp % 3600 or (previous is not None and stamp <= previous):
            raise ValueError("expected ordered UTC hours")
        previous = stamp
        row = dict(zip(UNITS, values, strict=True))
        for key, value in row.items():
            if value is None:
                continue
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError("invalid weather value")
            if key != "temperature_2m" and (value < 0 or (key == "relative_humidity_2m" and value > 100)):
                raise ValueError("weather value out of range")
        if any(value is not None for value in values):
            series[datetime.fromtimestamp(stamp, timezone.utc)] = row
    return series


def fetch_weather():
    with urlopen(FEED, timeout=12) as response:
        return parse_weather(json.load(response))


def weather_window(series, first, count):
    rows = []
    available = 0
    for offset in range(count):
        hour = first + offset * HOUR
        values = series.get(hour)
        available += values is not None
        rows.append({"timestamp": hour.isoformat(), **(values or dict.fromkeys(UNITS))})
    return {"hours": rows, "available_hours": available, "units": UNITS}
