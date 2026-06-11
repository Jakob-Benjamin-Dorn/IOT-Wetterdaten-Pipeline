import os
from dataclasses import dataclass
from datetime import datetime

import psycopg


@dataclass
class StoredReading:
    device_id: str
    received_at: datetime
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float
    raw_s3_bucket: str
    raw_s3_key: str


def get_connection_string() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "weather")
    user = os.getenv("POSTGRES_USER", "weather")
    password = os.getenv("POSTGRES_PASSWORD", "weather")

    return f"host={host} port={port} dbname={db} user={user} password={password}"


def insert_reading(reading: StoredReading) -> None:
    sql = """
        INSERT INTO weather_readings (
            device_id,
            received_at,
            temperature_c,
            humidity_pct,
            pressure_hpa,
            raw_s3_bucket,
            raw_s3_key
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    reading.device_id,
                    reading.received_at,
                    reading.temperature_c,
                    reading.humidity_pct,
                    reading.pressure_hpa,
                    reading.raw_s3_bucket,
                    reading.raw_s3_key,
                ),
            )
