#!/usr/bin/env python3

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import psycopg

from src.collector.fallback import should_use_fallback


def get_connection_string() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "weather")
    user = os.getenv("POSTGRES_USER", "weather")
    password = os.getenv("POSTGRES_PASSWORD", "weather")

    return f"host={host} port={port} dbname={db} user={user} password={password}"


def get_latest_sensor_timestamp():
    sql = """
        SELECT received_at
        FROM weather_readings
        WHERE source = 'sensor'
        ORDER BY received_at DESC
        LIMIT 1
    """

    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            row = cur.fetchone()

    if row is None:
        return None

    return row[0]


def run_openweather_fetch() -> None:
    script_path = PROJECT_ROOT / "scripts" / "fallback" / "fetch-openweather-reading.py"

    if not script_path.exists():
        print(f"OpenWeather-Skript nicht gefunden: {script_path}", file=sys.stderr)
        sys.exit(1)

    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    threshold_seconds = int(os.getenv("FALLBACK_THRESHOLD_SECONDS", "120"))

    latest_sensor_timestamp = get_latest_sensor_timestamp()
    use_fallback, reason = should_use_fallback(
        latest_sensor_timestamp,
        now=datetime.now(timezone.utc),
        threshold_seconds=threshold_seconds,
    )

    print(f"Fallback-Prüfung: {reason}")

    if not use_fallback:
        print("Kein Fallback nötig.")
        return

    print("Fallback wird ausgelöst: OpenWeather wird abgerufen.")
    run_openweather_fetch()


if __name__ == "__main__":
    main()
