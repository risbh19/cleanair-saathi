"""Render the public Delhi brief; sending requires an explicitly configured destination."""
import argparse
import json
import os
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def render(data):
    band = (data.get("hourly_subindex_estimate") or {}).get("band")
    level = data.get("hourly_pm25_ug_m3")
    label = f"{level:g} µg/m³" if level is not None else "unavailable"
    stale = " · older data" if data.get("stale") else ""
    return (f"CleanAir Saathi · Delhi · {data['data_mode']}{stale}\n"
            f"PM2.5: {label} · {band or 'band unavailable'}\n"
            f"{data['as_of']} · {data['source']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--send", action="store_true")
    args = parser.parse_args()
    try:
        with urlopen(args.api.rstrip("/") + "/air/now", timeout=10) as response:
            message = render(json.load(response))
        if not args.send:
            print(message)
            return
        token, chat = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHAT_ID"]
        params = urlencode({"chat_id": chat, "text": message}).encode()
        req = Request(f"https://api.telegram.org/bot{token}/sendMessage", data=params)
        with urlopen(req, timeout=10) as response:
            if not json.load(response).get("ok"):
                raise ValueError("delivery failed")
    except (URLError, OSError, ValueError, KeyError):
        parser.exit(1, "Brief unavailable or delivery failed. Check the API, destination and credentials.\n")


if __name__ == "__main__":
    main()
