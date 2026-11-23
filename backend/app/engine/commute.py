"""One-way commute scenarios for one passenger."""
from typing import Literal

from fastapi import APIRouter, HTTPException
from psycopg import OperationalError
from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.db.migrate import connect

router = APIRouter(tags=["Simulations"])
Mode = Literal["petrol_hatchback_lt1000cc", "scooter_lt110cc", "cng_auto", "intracity_bus"]


class Inputs(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class Exposure(Inputs):
    pm25_ug_m3: float = Field(ge=0, le=10000)
    duration_min: float = Field(gt=0, le=1440)
    breathing_m3_h: float = Field(gt=0, le=10)


class Leg(Inputs):
    mode: Mode
    travellers: int = Field(default=1, ge=1, le=10)
    exposure: Exposure | None = None

    @model_validator(mode="after")
    def check_travellers(self):
        limits = {"petrol_hatchback_lt1000cc": 5, "scooter_lt110cc": 2, "cng_auto": 3, "intracity_bus": 1}
        if self.travellers > limits[self.mode]:
            raise ValueError("Traveller count exceeds the supported scenario")
        return self


class Comparison(Inputs):
    distance_km: float = Field(gt=0, le=500)
    baseline: Leg
    alternative: Leg


def estimate(leg, km, factors):
    rate, basis, year, url = factors[leg.mode]
    per_passenger = float(rate) / leg.travellers if basis == "vehicle" else float(rate)
    exposure = leg.exposure
    return {**leg.model_dump(), "factor_g_co2_per_km": float(rate), "factor_basis": basis,
            "vintage": year, "source_url": url, "g_co2_per_passenger_km": per_passenger,
            "trip_co2_g": km * per_passenger,
            "inhaled_pm25_ug": (exposure.pm25_ug_m3 * exposure.duration_min / 60 * exposure.breathing_m3_h
                                if exposure else None)}


@router.post("/simulate/commute")
def compare(inputs: Comparison):
    try:
        with connect() as db:
            rows = db.execute("""SELECT mode, grams_co2_per_km, basis, vintage, source_url
                                 FROM emission_factors WHERE mode IN (%s, %s)""",
                              (inputs.baseline.mode, inputs.alternative.mode)).fetchall()
    except OperationalError:
        raise HTTPException(503, "Emission factor store unavailable") from None
    factors = {mode: values for mode, *values in rows}
    if not {inputs.baseline.mode, inputs.alternative.mode} <= factors.keys():
        raise HTTPException(503, "Emission factor unavailable")
    base = estimate(inputs.baseline, inputs.distance_km, factors)
    alt = estimate(inputs.alternative, inputs.distance_km, factors)
    return {"distance_km": inputs.distance_km, "baseline": base, "alternative": alt,
            "co2_difference_g": base["trip_co2_g"] - alt["trip_co2_g"],
            "inhaled_difference_ug": (base["inhaled_pm25_ug"] - alt["inhaled_pm25_ug"]
                                      if inputs.baseline.exposure and inputs.alternative.exposure else None)}
