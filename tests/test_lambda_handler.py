import json
from datetime import datetime, timezone

from src.collector.lambda_handler import lambda_handler
from src.collector.raw_storage import RawStorageResult


def authorized_event(body: str) -> dict:
    return {
        "headers": {
            "x-collector-token": "test-token",
        },
        "body": body,
    }


def test_lambda_handler_accepts_valid_sensor_payload(monkeypatch):
    def fake_store_raw_reading(**kwargs):
        return RawStorageResult(
            status="accepted",
            source=kwargs["source"],
            bucket="weather-raw",
            key="raw_readings/test.json",
            received_at=datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc),
        )

    monkeypatch.setattr(
        "src.collector.lambda_handler.store_raw_reading",
        fake_store_raw_reading,
    )
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    event = authorized_event(
        json.dumps(
            {
                "device_id": "esp32-c6-window-01",
                "temperature_c": 22.5,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        )
    )

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 202
    assert body["status"] == "accepted"
    assert body["source"] == "sensor"


def test_lambda_handler_rejects_invalid_json(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    event = authorized_event("{not-json")

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "Invalid JSON body" in body["detail"]


def test_lambda_handler_rejects_invalid_sensor_payload(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    event = authorized_event(
        json.dumps(
            {
                "device_id": "esp32-c6-window-01",
                "temperature_c": 99.0,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        )
    )

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 422
    assert body["detail"][0]["loc"] == ["temperature_c"]


def test_lambda_handler_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    event = {
        "body": json.dumps(
            {
                "device_id": "lambda-test-device",
                "temperature_c": 22.5,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        )
    }

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 401
    assert body["detail"] == "Unauthorized"


def test_lambda_handler_rejects_wrong_token(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    event = {
        "headers": {
            "x-collector-token": "wrong-token",
        },
        "body": json.dumps(
            {
                "device_id": "lambda-test-device",
                "temperature_c": 22.5,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        ),
    }

    result = lambda_handler(event, None)

    assert result["statusCode"] == 401