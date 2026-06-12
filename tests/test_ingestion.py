from datetime import datetime, timezone

from src.collector.ingestion import build_s3_key


def test_build_s3_key_partitions_by_source_and_device_id():
    received_at = datetime(2026, 6, 11, 16, 10, 37, tzinfo=timezone.utc)

    key = build_s3_key(
        source="openweather",
        device_id="openweather-reference",
        received_at=received_at,
    )

    assert key.startswith(
        "raw_readings/source=openweather/device_id=openweather-reference/"
    )
    assert "year=2026/month=06/day=11/hour=16/" in key
    assert key.endswith(".json")
