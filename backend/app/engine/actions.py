"""Select daily actions in catalogue priority order."""
import json
from pathlib import Path

CATALOGUE = json.loads((Path(__file__).resolve().parents[2] / "data/actions.json").read_text(encoding="utf-8"))


def daily_actions(profile, band):
    members = profile["members"]
    modes = {trip["mode"] for member in members for trip in member["commutes"]}
    facts = {
        "high": band in {"Very poor", "Severe"},
        "sensitive": any(m["sensitive"] for m in members),
        "child": any(m["age_band"] == "child" for m in members),
        "biomass": profile["cooking_fuel"] == "biomass",
        "purifier": profile["purifier_cadr_m3h"] > 0,
        "commute": bool(modes),
        "motor": bool(modes & {"car", "two_wheeler"}),
    }
    eligible = [action for action in CATALOGUE if all(facts[key] for key in action["requires"])]
    return [{key: action[key] for key in ("id", "en", "hi")} for action in eligible[:7]]
