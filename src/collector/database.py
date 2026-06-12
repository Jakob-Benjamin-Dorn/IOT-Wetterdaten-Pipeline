import os
from dataclasses import dataclass
from datetime import datetime

import psycopg

from src.collector.config import get_settings


@dataclass
class StoredReading:
    source: str
    device_id: str
    received_at: datetime
    temperature_c: float
    humidity_pct: float
    pressure_hpa: float
    raw_s3_bucket: str
    raw_s3_key: str


def get_connection_string() -> str:
    settings = get_settings()

    return (
        f"host={settings.postgres_host} "
        f"port={settings.postgres_port} "
        f"dbname={settings.postgres_db} "
        f"user={settings.postgres_user} "
        f"password={settings.postgres_password}"
    )


def insert_reading(reading: StoredReading) -> None:
    sql = """
        INSERT INTO weather_readings (
            source,
            device_id,
            received_at,
            temperature_c,
            humidity_pct,
            pressure_hpa,
            raw_s3_bucket,
            raw_s3_key
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    with psycopg.connect(get_connection_string()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    reading.source,
                    reading.device_id,
                    reading.received_at,
                    reading.temperature_c,
                    reading.humidity_pct,
                    reading.pressure_hpa,
                    reading.raw_s3_bucket,
                    reading.raw_s3_key,
                ),
            )
