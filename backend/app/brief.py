"""Read an hourly series for one location and report its PM2.5 sub-index."""

import argparse
import csv
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from math import fsum
from pathlib import Path

from .services.aqi import pm25_subindex


def air_brief(readings: dict[datetime, float], as_of: datetime) -> dict:
    """as_of is the last included hourly slot. Missing slots stay missing."""
    if as_of.utcoffset() is None:
        raise ValueError("as_of must carry a UTC offset")
    as_of = as_of.astimezone(timezone.utc)
    if as_of.minute or as_of.second or as_of.microsecond:
        raise ValueError("as_of must be aligned to a UTC hour")
    window = [readings[hour] for offset in range(24)
              if (hour := as_of - timedelta(hours=offset)) in readings]
    for concentration in window:
        pm25_subindex(concentration)
    current = readings.get(as_of)
    mean = fsum(window) / len(window) if len(window) >= 16 else None
    return {
        "as_of": as_of.isoformat(),
        "hourly_pm25_ug_m3": current,
        "hourly_subindex_estimate": asdict(pm25_subindex(current)) if current is not None else None,
        "valid_hours": len(window),
        "mean_24h_pm25_ug_m3": mean,
        "pm25_subindex_24h": asdict(pm25_subindex(mean)) if mean is not None else None,
    }


def load_csv(path: Path) -> dict[datetime, float]:
    readings = {}
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            hour = datetime.fromisoformat(row["timestamp"])
            if hour.utcoffset() is None:
                raise ValueError("timestamp must carry a UTC offset")
            hour = hour.astimezone(timezone.utc)
            if hour.minute or hour.second or hour.microsecond or hour in readings:
                raise ValueError("expected one reading per distinct UTC hour")
            concentration = float(row["pm25_ug_m3"])
            pm25_subindex(concentration)
            readings[hour] = concentration
    if not readings:
        raise ValueError("no hourly readings supplied")
    return readings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--as-of", help="Last included hour, e.g. 2025-11-01T23:00:00+00:00")
    args = parser.parse_args()
    try:
        series = load_csv(args.csv)
        end = datetime.fromisoformat(args.as_of) if args.as_of else max(series)
        print(json.dumps(air_brief(series, end), indent=2))
    except (KeyError, ValueError, OSError) as exc:
        parser.exit(2, f"Invalid hourly series: {exc}\n")
