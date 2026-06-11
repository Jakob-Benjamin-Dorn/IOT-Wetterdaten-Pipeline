#!/usr/bin/env python3

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg


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


def should_use_fallback(latest_sensor_timestamp, threshold_seconds: int) -> tuple[bool, str]:
    if latest_sensor_timestamp is None:
        return True, "kein Sensorwert vorhanden"

    now = datetime.now(timezone.utc)

    if latest_sensor_timestamp.tzinfo is None:
        latest_sensor_timestamp = latest_sensor_timestamp.replace(tzinfo=timezone.utc)

    age_seconds = (now - latest_sensor_timestamp).total_seconds()

    if age_seconds > threshold_seconds:
        return True, f"letzter Sensorwert ist {age_seconds:.0f}s alt"

    return False, f"Sensorwert ist aktuell ({age_seconds:.0f}s alt)"


def run_openweather_fetch() -> None:
    script_path = Path(__file__).parent / "fetch-openweather-reading.py"

    if not script_path.exists():
        print(f"OpenWeather-Skript nicht gefunden: {script_path}", file=sys.stderr)
        sys.exit(1)

    subprocess.run([sys.executable, str(script_path)], check=True)


def main() -> None:
    threshold_seconds = int(os.getenv("FALLBACK_THRESHOLD_SECONDS", "120"))

    latest_sensor_timestamp = get_latest_sensor_timestamp()
    use_fallback, reason = should_use_fallback(latest_sensor_timestamp, threshold_seconds)

    print(f"Fallback-Prüfung: {reason}")

    if not use_fallback:
        print("Kein Fallback nötig.")
        return

    print("Fallback wird ausgelöst: OpenWeather wird abgerufen.")
    run_openweather_fetch()


if __name__ == "__main__":
    main()
