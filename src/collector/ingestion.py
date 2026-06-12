import json
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError

from src.collector.config import get_settings
from src.collector.database import StoredReading, insert_reading
from src.collector.exceptions import CollectorStorageError


def get_s3_client():
    settings = get_settings()

    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.aws_region,
    }

    if settings.localstack_endpoint:
        client_kwargs["endpoint_url"] = settings.localstack_endpoint

    return boto3.client(**client_kwargs)


def ensure_bucket_exists() -> None:
    settings = get_settings()
    s3 = get_s3_client()

    try:
        s3.head_bucket(Bucket=settings.raw_bucket)
    except ClientError:
        s3.create_bucket(
            Bucket=settings.raw_bucket,
            CreateBucketConfiguration={
                "LocationConstraint": settings.aws_region,
            },
        )


def build_s3_key(source: str, device_id: str, received_at: datetime) -> str:
    timestamp = received_at.strftime("%Y%m%dT%H%M%SZ")
    unique_id = uuid4()

    return (
        f"raw_readings/"
        f"source={source}/"
        f"device_id={device_id}/"
        f"year={received_at:%Y}/"
        f"month={received_at:%m}/"
        f"day={received_at:%d}/"
        f"hour={received_at:%H}/"
        f"{timestamp}-{unique_id}.json"
    )


def store_reading(
    *,
    source: str,
    device_id: str,
    temperature_c: float,
    humidity_pct: float,
    pressure_hpa: float,
    payload: dict,
):
    settings = get_settings()

    received_at = datetime.now(timezone.utc)
    s3_key = build_s3_key(source, device_id, received_at)

    raw_record = {
        "received_at": received_at.isoformat(),
        "source": source,
        "payload": payload,
    }

    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=settings.raw_bucket,
            Key=s3_key,
            Body=json.dumps(raw_record).encode("utf-8"),
            ContentType="application/json",
        )
    except ClientError as exc:
        raise CollectorStorageError(f"Could not write reading to S3: {exc}") from exc

    insert_reading(
        StoredReading(
            source=source,
            device_id=device_id,
            received_at=received_at,
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            pressure_hpa=pressure_hpa,
            raw_s3_bucket=settings.raw_bucket,
            raw_s3_key=s3_key,
        )
    )

    return {
        "status": "accepted",
        "source": source,
        "bucket": settings.raw_bucket,
        "key": s3_key,
    }
