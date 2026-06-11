#!/usr/bin/env python3

import json
import os
import sys
import urllib.parse
import urllib.request


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"Missing environment variable: {name}", file=sys.stderr)
        sys.exit(1)
    return value


def fetch_openweather() -> dict:
    api_key = require_env("OPENWEATHER_API_KEY")
    lat = require_env("OPENWEATHER_LAT")
    lon = require_env("OPENWEATHER_LON")

    query = urllib.parse.urlencode(
        {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
        }
    )

    url = f"{OPENWEATHER_URL}?{query}"

    with urllib.request.urlopen(url, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"OpenWeather returned HTTP {response.status}")

        return json.loads(response.read().decode("utf-8"))


def normalize_openweather(raw: dict) -> dict:
    main = raw.get("main", {})

    try:
        return {
            "location": "openweather-reference",
            "temperature_c": float(main["temp"]),
            "humidity_pct": float(main["humidity"]),
            "pressure_hpa": float(main["pressure"]),
        }
    except KeyError as exc:
        raise RuntimeError(f"OpenWeather response is missing field: {exc}") from exc


def post_to_collector(payload: dict) -> dict:
    collector_url = os.getenv(
        "FALLBACK_COLLECTOR_URL",
        "http://localhost:8088/fallback-readings",
    )

    request = urllib.request.Request(
        collector_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    raw = fetch_openweather()
    normalized = normalize_openweather(raw)
    result = post_to_collector(normalized)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()