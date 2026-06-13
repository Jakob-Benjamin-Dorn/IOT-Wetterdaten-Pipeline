from dataclasses import dataclass
from datetime import datetime

import psycopg

from src.collector.config import get_settings
from src.collector.exceptions import CollectorStorageError


@dataclass(frozen=True)
class NormalizedReading:
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
        f"password={settings.postgres_password} "
        f"connect_timeout=5"
    )


def ensure_schema_exists(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weather_readings (
                id BIGSERIAL PRIMARY KEY,

                source TEXT NOT NULL DEFAULT 'sensor',
                device_id TEXT NOT NULL,
                received_at TIMESTAMPTZ NOT NULL,

                temperature_c DOUBLE PRECISION NOT NULL,
                humidity_pct DOUBLE PRECISION NOT NULL,
                pressure_hpa DOUBLE PRECISION NOT NULL,

                raw_s3_bucket TEXT NOT NULL,
                raw_s3_key TEXT NOT NULL,

                created_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_weather_readings_device_time
            ON weather_readings (device_id, received_at DESC);
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_weather_readings_source_time
            ON weather_readings (source, received_at DESC);
            """
        )


def insert_normalized_reading(reading: NormalizedReading) -> None:
    try:
        with psycopg.connect(get_connection_string()) as conn:
            ensure_schema_exists(conn)

            with conn.cursor() as cur:
                cur.execute(
                    """
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
                    """,
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

            conn.commit()

    except psycopg.Error as exc:
        raise CollectorStorageError(f"Could not write reading to RDS: {exc}") from exc


def get_latest_readings(limit: int = 10, source: str | None = None) -> list[dict]:
    safe_limit = max(1, min(limit, 100))

    try:
        with psycopg.connect(get_connection_string()) as conn:
            ensure_schema_exists(conn)

            with conn.cursor() as cur:
                if source:
                    cur.execute(
                        """
                        SELECT
                            source,
                            device_id,
                            received_at,
                            temperature_c,
                            humidity_pct,
                            pressure_hpa,
                            raw_s3_bucket,
                            raw_s3_key
                        FROM weather_readings
                        WHERE source = %s
                        ORDER BY received_at DESC
                        LIMIT %s
                        """,
                        (source, safe_limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            source,
                            device_id,
                            received_at,
                            temperature_c,
                            humidity_pct,
                            pressure_hpa,
                            raw_s3_bucket,
                            raw_s3_key
                        FROM weather_readings
                        ORDER BY received_at DESC
                        LIMIT %s
                        """,
                        (safe_limit,),
                    )

                rows = cur.fetchall()

        return [
            {
                "source": row[0],
                "device_id": row[1],
                "received_at": row[2].isoformat(),
                "temperature_c": row[3],
                "humidity_pct": row[4],
                "pressure_hpa": row[5],
                "raw_s3_bucket": row[6],
                "raw_s3_key": row[7],
            }
            for row in rows
        ]

    except psycopg.Error as exc:
        raise CollectorStorageError(f"Could not read latest readings from RDS: {exc}") from exc