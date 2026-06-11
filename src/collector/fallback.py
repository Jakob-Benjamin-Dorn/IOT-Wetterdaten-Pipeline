from datetime import datetime, timezone


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def should_use_fallback(
    latest_sensor_timestamp: datetime | None,
    *,
    now: datetime,
    threshold_seconds: int,
) -> tuple[bool, str]:
    if threshold_seconds <= 0:
        raise ValueError("threshold_seconds must be greater than 0")

    if latest_sensor_timestamp is None:
        return True, "kein Sensorwert vorhanden"

    now_utc = ensure_utc(now)
    latest_sensor_utc = ensure_utc(latest_sensor_timestamp)

    age_seconds = (now_utc - latest_sensor_utc).total_seconds()

    if age_seconds >= threshold_seconds:
        return True, f"letzter Sensorwert ist {age_seconds:.0f}s alt"

    return False, f"Sensorwert ist aktuell ({age_seconds:.0f}s alt)"
