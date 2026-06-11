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

CREATE INDEX IF NOT EXISTS idx_weather_readings_device_time
ON weather_readings (device_id, received_at DESC);
