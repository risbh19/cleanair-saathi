"""Hourly equilibrium estimates for outdoor particles entering a single room."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

Concentration = Annotated[float, Field(ge=0, le=10000)]
METHOD_URL = "https://www.epa.gov/system/files/documents/2023-08/APEX52_UsersGuide_Vol2_June2023.pdf"


class RoomScenario(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)

    outdoor_pm25_ug_m3: list[Concentration] = Field(min_length=1, max_length=48)
    floor_area_m2: float = Field(ge=1, le=1000)
    ceiling_height_m: float = Field(ge=1, le=15)
    windows: Literal["open", "closed"] = "closed"
    purifier_cadr_m3_h: float = Field(default=0, ge=0, le=10000)
    penetration_fraction: float = Field(default=0.8, ge=0, le=1)
    closed_air_changes_h: float = Field(default=0.7, gt=0, le=30)
    open_air_changes_h: float = Field(default=4, gt=0, le=30)
    deposition_rate_h: float = Field(default=0.2, ge=0, le=15)
    breathing_rate_m3_h: float = Field(default=0.4, gt=0, le=10)
    target_clean_air_changes_h: float = Field(default=4.8, gt=0, le=30)


def simulate(room: RoomScenario) -> dict:
    volume = room.floor_area_m2 * room.ceiling_height_m
    exchange = room.open_air_changes_h if room.windows == "open" else room.closed_air_changes_h

    def estimate(exchange_rate: float, cadr: float) -> dict:
        fraction = room.penetration_fraction * exchange_rate / (
            exchange_rate + room.deposition_rate_h + cadr / volume
        )
        hourly = [value * fraction for value in room.outdoor_pm25_ug_m3]
        return {
            "hourly_pm25_ug_m3": hourly,
            "inhaled_pm25_ug": sum(hourly) * room.breathing_rate_m3_h,
        }

    baseline = estimate(room.closed_air_changes_h, 0)
    selected = estimate(exchange, room.purifier_cadr_m3_h)
    avoided = baseline["inhaled_pm25_ug"] - selected["inhaled_pm25_ug"]
    return {
        "model": "hourly_equilibrium",
        "method_url": METHOD_URL,
        "assumptions": room.model_dump(),
        "limitations": "One well-mixed room. Each hour is at equilibrium. Indoor particle sources are excluded. Defaults are illustrative scenario inputs.",
        "room_volume_m3": volume,
        "cadr_for_target_m3_h": volume * room.target_clean_air_changes_h,
        "baseline_closed_no_purifier": baseline,
        "selected": selected,
        "avoided_inhaled_pm25_ug": avoided,
        "reduction_percent": 100 * avoided / baseline["inhaled_pm25_ug"] if baseline["inhaled_pm25_ug"] else None,
    }
