"""PM2.5 component of India's National AQI. Concentrations are in µg/m³."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class SubIndex:
    band: str
    value: int | None


# Upper limits from the National AQI breakpoint table.
BREAKPOINTS = (
    (30, 50, "Good"),
    (60, 100, "Satisfactory"),
    (90, 200, "Moderately polluted"),
    (120, 300, "Poor"),
    (250, 400, "Very poor"),
)


def pm25_subindex(concentration: float) -> SubIndex:
    if not isfinite(concentration) or concentration < 0:
        raise ValueError("PM2.5 must be finite and non-negative")

    lower, previous = 0, 0
    for upper, limit, band in BREAKPOINTS:
        if concentration <= upper:
            estimate = previous + (concentration - lower) * (limit - previous) / (upper - lower)
            # Truncate for display. Keep fractional inputs above a cutoff in their band.
            minimum = previous + 1 if lower else 0
            return SubIndex(band, max(minimum, int(estimate)))
        lower, previous = upper, limit

    # The published severe concentration interval has no upper breakpoint.
    return SubIndex("Severe", None)
