import json
import hmac
import os

from pydantic import ValidationError

from src.collector.exceptions import CollectorStorageError
from src.collector.models import SensorReading
from src.collector.raw_storage import store_raw_reading


TOKEN_HEADER_NAME = "x-collector-token"


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


def lambda_handler(event, context):
    if not is_authorized(event):
        return response(401, {"detail": "Unauthorized"})

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
    except CollectorStorageError as exc:
        return response(500, {"detail": str(exc)})

    return response(202, result.to_response_dict())