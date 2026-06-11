from datetime import datetime, timedelta, timezone

import pytest

from src.collector.fallback import should_use_fallback


def test_fallback_is_used_when_no_sensor_reading_exists():
    use_fallback, reason = should_use_fallback(
        None,
        now=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
        threshold_seconds=120,
    )

    assert use_fallback is True
    assert reason == "kein Sensorwert vorhanden"


def test_fallback_is_not_used_when_sensor_reading_is_fresh():
    now = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)
    latest_sensor_timestamp = now - timedelta(seconds=30)

    use_fallback, reason = should_use_fallback(
        latest_sensor_timestamp,
        now=now,
        threshold_seconds=120,
    )

    assert use_fallback is False
    assert "Sensorwert ist aktuell" in reason


def test_fallback_is_used_when_sensor_reading_is_too_old():
    now = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)
    latest_sensor_timestamp = now - timedelta(seconds=300)

    use_fallback, reason = should_use_fallback(
        latest_sensor_timestamp,
        now=now,
        threshold_seconds=120,
    )

    assert use_fallback is True
    assert "letzter Sensorwert ist 300s alt" in reason


def test_fallback_is_used_when_sensor_age_equals_threshold():
    now = datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc)
    latest_sensor_timestamp = now - timedelta(seconds=120)

    use_fallback, reason = should_use_fallback(
        latest_sensor_timestamp,
        now=now,
        threshold_seconds=120,
    )

    assert use_fallback is True
    assert "letzter Sensorwert ist 120s alt" in reason


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError):
        should_use_fallback(
            datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
            now=datetime(2026, 6, 11, 12, 0, tzinfo=timezone.utc),
            threshold_seconds=0,
        )
