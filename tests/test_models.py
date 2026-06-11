import pytest
from pydantic import ValidationError

from src.collector.models import FallbackWeatherReading, SensorReading


def test_valid_sensor_reading_is_accepted():
    reading = SensorReading.model_validate(
        {
            "device_id": "esp32-c6-window-01",
            "temperature_c": 22.5,
            "humidity_pct": 45.0,
            "pressure_hpa": 1013.2,
        }
    )

    assert reading.device_id == "esp32-c6-window-01"
    assert reading.temperature_c == 22.5
    assert reading.humidity_pct == 45.0
    assert reading.pressure_hpa == 1013.2


def test_sensor_reading_rejects_unrealistic_temperature():
    with pytest.raises(ValidationError):
        SensorReading.model_validate(
            {
                "device_id": "esp32-c6-window-01",
                "temperature_c": -25.6,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        )


def test_sensor_reading_rejects_invalid_pressure():
    with pytest.raises(ValidationError):
        SensorReading.model_validate(
            {
                "device_id": "esp32-c6-window-01",
                "temperature_c": 22.5,
                "humidity_pct": 45.0,
                "pressure_hpa": -157.16,
            }
        )


def test_fallback_reading_uses_default_location():
    reading = FallbackWeatherReading.model_validate(
        {
            "temperature_c": 20.1,
            "humidity_pct": 50.0,
            "pressure_hpa": 1011.0,
        }
    )

    assert reading.location == "openweather-reference"
