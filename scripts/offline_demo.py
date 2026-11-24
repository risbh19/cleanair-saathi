"""Regenerate the offline phone demo from the same fixtures and models as the API."""
import json
from pathlib import Path

from backend.app.brief import air_brief, load_csv
from backend.app.engine.actions import daily_actions
from backend.app.engine.indoor import RoomScenario, simulate
from backend.app.services.forecast import HOUR, forecast


def build():
    fixtures = Path("backend/data/fixtures")
    day = load_csv(fixtures / "synthetic_day.csv")
    latest = max(day)
    brief = air_brief(day, latest)
    air = forecast(load_csv(fixtures / "synthetic_forecast.csv"), latest + HOUR, 48)
    profile = {"members": [{"age_band": "adult", "sensitive": False, "commutes": [{"mode": "car"}]},
                           {"age_band": "child", "sensitive": True, "commutes": []}],
               "purifier_cadr_m3h": 200, "cooking_fuel": "lpg"}
    actions = daily_actions(profile, brief["hourly_subindex_estimate"]["band"])
    simulations = []
    for window in ("closed", "open"):
        for cadr in (0, 100, 200, 300):
            room = RoomScenario(floor_area_m2=12, ceiling_height_m=2.7, windows=window, purifier_cadr_m3_h=cadr,
                                outdoor_pm25_ug_m3=[row["pm25_ug_m3"] for row in air["hours"][:8]])
            result = simulate(room)
            simulations.append(dict(windows=window, cadr=cadr, dose=result["selected"]["inhaled_pm25_ug"]))
    return dict(as_of=brief["as_of"], pm25=brief["hourly_pm25_ug_m3"], actions=actions, simulations=simulations,
                forecast=[{"timestamp": r["timestamp"], "pm25": r["pm25_ug_m3"]} for r in air["hours"]])


if __name__ == "__main__":
    Path("frontend/src/offline-demo.json").write_text(json.dumps(build(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
