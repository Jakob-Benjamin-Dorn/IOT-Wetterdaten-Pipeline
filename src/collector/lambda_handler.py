import json
import hmac
import os

from pydantic import ValidationError

from src.collector.exceptions import CollectorStorageError
from src.collector.models import SensorReading
from src.collector.raw_storage import store_raw_reading
from src.collector.rds_storage import (
    NormalizedReading,
    get_latest_readings,
    insert_normalized_reading,
)


TOKEN_HEADER_NAME = "x-collector-token"


def get_request_method(event: dict) -> str:
    return (
        event.get("requestContext", {})
        .get("http", {})
        .get("method", "POST")
        .upper()
    )


def get_request_path(event: dict) -> str:
    return event.get("rawPath") or event.get("path") or "/sensor-readings"


def handle_sensor_reading(event: dict) -> dict:
    try:
        payload = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        return response(400, {"detail": f"Invalid JSON body: {exc}"})

    try:
        reading = SensorReading.model_validate(payload)
    except ValidationError as exc:
        return response(422, {"detail": exc.errors()})

    try:
        result = store_raw_reading(
            source="sensor",
            device_id=reading.device_id,
            payload=payload,
        )

        insert_normalized_reading(
            NormalizedReading(
                source="sensor",
                device_id=reading.device_id,
                received_at=result.received_at,
                temperature_c=reading.temperature_c,
                humidity_pct=reading.humidity_pct,
                pressure_hpa=reading.pressure_hpa,
                raw_s3_bucket=result.bucket,
                raw_s3_key=result.key,
            )
        )

    except CollectorStorageError as exc:
        return response(500, {"detail": str(exc)})

    return response(202, result.to_response_dict())


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
        },
        "body": json.dumps(body),
    }


def get_header(event: dict, header_name: str) -> str | None:
    headers = event.get("headers") or {}

    for key, value in headers.items():
        if key.lower() == header_name.lower():
            return value

    return None


def is_authorized(event: dict) -> bool:
    expected_token = os.getenv("COLLECTOR_TOKEN")

    if not expected_token:
        return False

    provided_token = get_header(event, TOKEN_HEADER_NAME)

    if not provided_token:
        return False

    return hmac.compare_digest(provided_token, expected_token)


def handle_latest_readings() -> dict:
    try:
        readings = get_latest_readings(limit=10)
    except CollectorStorageError as exc:
        return response(500, {"detail": str(exc)})

    return response(
        200,
        {
            "count": len(readings),
            "readings": readings,
        },
    )


def lambda_handler(event, context):
    if not is_authorized(event):
        return response(401, {"detail": "Unauthorized"})

    method = get_request_method(event)
    path = get_request_path(event)

    if method == "GET" and path == "/latest-readings":
        return handle_latest_readings()

    if method == "POST" and path in ["/sensor-readings", "/readings"]:
        return handle_sensor_reading(event)

    return response(
        404,
        {
            "detail": "Route not found",
            "method": method,
            "path": path,
        },
    )