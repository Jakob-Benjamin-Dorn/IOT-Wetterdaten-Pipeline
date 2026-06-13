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

    def fake_insert_normalized_reading(reading):
        assert reading.source == "sensor"
        assert reading.device_id == "esp32-c6-window-01"
        assert reading.raw_s3_bucket == "weather-raw"
        assert reading.raw_s3_key == "raw_readings/test.json"

    monkeypatch.setattr(
        "src.collector.lambda_handler.store_raw_reading",
        fake_store_raw_reading,
    )

    monkeypatch.setattr(
        "src.collector.lambda_handler.insert_normalized_reading",
        fake_insert_normalized_reading,
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


def test_lambda_handler_returns_500_when_rds_write_fails(monkeypatch):
    def fake_store_raw_reading(**kwargs):
        return RawStorageResult(
            status="accepted",
            source=kwargs["source"],
            bucket="weather-raw",
            key="raw_readings/test.json",
            received_at=datetime(2026, 6, 12, 12, 0, tzinfo=timezone.utc),
        )

    def fake_insert_normalized_reading(reading):
        from src.collector.exceptions import CollectorStorageError

        raise CollectorStorageError("Could not write reading to RDS")

    monkeypatch.setattr(
        "src.collector.lambda_handler.store_raw_reading",
        fake_store_raw_reading,
    )
    monkeypatch.setattr(
        "src.collector.lambda_handler.insert_normalized_reading",
        fake_insert_normalized_reading,
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

    assert result["statusCode"] == 500
    assert "Could not write reading to RDS" in body["detail"]


def test_lambda_handler_returns_latest_readings(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    def fake_get_latest_readings(limit=10):
        return [
            {
                "source": "sensor",
                "device_id": "esp32-c6-window-01",
                "received_at": "2026-06-13T08:00:00+00:00",
                "temperature_c": 22.1,
                "humidity_pct": 53.2,
                "pressure_hpa": 1010.8,
                "raw_s3_bucket": "weather-raw",
                "raw_s3_key": "raw_readings/test.json",
            }
        ]

    monkeypatch.setattr(
        "src.collector.lambda_handler.get_latest_readings",
        fake_get_latest_readings,
    )

    event = {
        "headers": {
            "x-collector-token": "test-token",
        },
        "requestContext": {
            "http": {
                "method": "GET",
            }
        },
        "rawPath": "/latest-readings",
    }

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 200
    assert body["count"] == 1
    assert body["readings"][0]["device_id"] == "esp32-c6-window-01"


def test_lambda_handler_returns_404_for_unknown_route(monkeypatch):
    monkeypatch.setenv("COLLECTOR_TOKEN", "test-token")

    event = {
        "headers": {
            "x-collector-token": "test-token",
        },
        "requestContext": {
            "http": {
                "method": "GET",
            }
        },
        "rawPath": "/unknown",
    }

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 404
    assert body["detail"] == "Route not found"