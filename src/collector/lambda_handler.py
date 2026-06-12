import json

from pydantic import ValidationError

from src.collector.exceptions import CollectorStorageError
from src.collector.raw_storage import store_raw_reading
from src.collector.models import SensorReading


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "content-type": "application/json",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    try:
        raw_body = event.get("body") or "{}"
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        return response(
            400,
            {
                "detail": f"Invalid JSON body: {exc}",
            },
        )

    try:
        reading = SensorReading.model_validate(payload)
    except ValidationError as exc:
        return response(
            422,
            {
                "detail": exc.errors(),
            },
        )

    try:
        result = store_raw_reading(
            source="sensor",
            device_id=reading.device_id,
            payload=payload,
        )
    except CollectorStorageError as exc:
        return response(
            500,
            {
                "detail": str(exc),
            },
        )

    return response(202, result.to_response_dict())
