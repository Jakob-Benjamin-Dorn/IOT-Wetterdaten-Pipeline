import json

from src.collector.lambda_handler import lambda_handler


def test_lambda_handler_accepts_valid_sensor_payload(monkeypatch):
    def fake_store_reading(**kwargs):
        return {
            "status": "accepted",
            "source": kwargs["source"],
            "bucket": "weather-raw",
            "key": "raw_readings/test.json",
        }

    monkeypatch.setattr(
        "src.collector.lambda_handler.store_raw_reading",
        fake_store_reading,
    )

    event = {
        "body": json.dumps(
            {
                "device_id": "esp32-c6-window-01",
                "temperature_c": 22.5,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        )
    }

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 202
    assert body["status"] == "accepted"
    assert body["source"] == "sensor"


def test_lambda_handler_rejects_invalid_json():
    event = {
        "body": "{not-json"
    }

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 400
    assert "Invalid JSON body" in body["detail"]


def test_lambda_handler_rejects_invalid_sensor_payload():
    event = {
        "body": json.dumps(
            {
                "device_id": "esp32-c6-window-01",
                "temperature_c": 99.0,
                "humidity_pct": 45.0,
                "pressure_hpa": 1013.2,
            }
        )
    }

    result = lambda_handler(event, None)
    body = json.loads(result["body"])

    assert result["statusCode"] == 422
    assert body["detail"][0]["loc"] == ["temperature_c"]
