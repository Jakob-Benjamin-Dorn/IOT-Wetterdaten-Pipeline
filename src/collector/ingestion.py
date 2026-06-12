from src.collector.raw_storage import store_raw_reading
from src.collector.database import StoredReading, insert_reading

def store_reading(
    *,
    source: str,
    device_id: str,
    temperature_c: float,
    humidity_pct: float,
    pressure_hpa: float,
    payload: dict,
):
    raw_result = store_raw_reading(
        source=source,
        device_id=device_id,
        payload=payload,
    )

    received_at = raw_result.received_at

    insert_reading(
        StoredReading(
            source=source,
            device_id=device_id,
            received_at=received_at,
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            pressure_hpa=pressure_hpa,
            raw_s3_bucket=raw_result.bucket,
            raw_s3_key=raw_result.key,
        )
    )

    return raw_result.to_response_dict()