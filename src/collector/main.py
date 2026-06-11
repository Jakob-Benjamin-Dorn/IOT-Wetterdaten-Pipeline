import json
import os
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from src.collector.database import StoredReading, insert_reading


AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "eu-central-1")
LOCALSTACK_ENDPOINT = os.getenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
RAW_BUCKET = os.getenv("RAW_BUCKET", "weather-raw")


app = FastAPI(title="Wetter IoT Collector")


class FallbackWeatherReading(BaseModel):
    temperature_c: float = Field(..., ge=-20, le=50)
    humidity_pct: float = Field(..., ge=0, le=100)
    pressure_hpa: float = Field(..., ge=800, le=1200)
    location: str = Field(default="local-openweather", max_length=120)


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=LOCALSTACK_ENDPOINT,
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "test"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "test"),
    )


def ensure_bucket_exists() -> None:
    s3 = get_s3_client()

    try:
        s3.head_bucket(Bucket=RAW_BUCKET)
    except ClientError:
        s3.create_bucket(
            Bucket=RAW_BUCKET,
            CreateBucketConfiguration={"LocationConstraint": AWS_REGION},
        )


def build_s3_key(device_id: str, received_at: datetime) -> str:
    return (
        "esp32_bme280/readings/"
        f"device_id={device_id}/"
        f"year={received_at:%Y}/"
        f"month={received_at:%m}/"
        f"day={received_at:%d}/"
        f"hour={received_at:%H}/"
        f"{received_at:%Y%m%dT%H%M%SZ}-{uuid4()}.json"
    )


@app.on_event("startup")
def startup() -> None:
    ensure_bucket_exists()


@app.get("/health")
def health():
    return {"status": "ok"}


def store_reading(
    *,
    source: str,
    device_id: str,
    temperature_c: float,
    humidity_pct: float,
    pressure_hpa: float,
    payload: dict,
):
    received_at = datetime.now(timezone.utc)
    s3_key = build_s3_key(device_id, received_at)

    raw_record = {
        "received_at": received_at.isoformat(),
        "source": source,
        "payload": payload,
    }

    try:
        s3 = get_s3_client()
        s3.put_object(
            Bucket=RAW_BUCKET,
            Key=s3_key,
            Body=json.dumps(raw_record).encode("utf-8"),
            ContentType="application/json",
        )
    except ClientError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not write reading to S3: {exc}",
        ) from exc

    insert_reading(
        StoredReading(
            source=source,
            device_id=device_id,
            received_at=received_at,
            temperature_c=temperature_c,
            humidity_pct=humidity_pct,
            pressure_hpa=pressure_hpa,
            raw_s3_bucket=RAW_BUCKET,
            raw_s3_key=s3_key,
        )
    )

    return {
        "status": "accepted",
        "source": source,
        "bucket": RAW_BUCKET,
        "key": s3_key,
    }

@app.post("/readings", status_code=202)
@app.post("/sensor-readings", status_code=202)
async def receive_reading(request: Request):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON body: {exc}",
        ) from exc

    try:
        reading = SensorReading(**payload)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sensor payload: {exc}",
        ) from exc

    return store_reading(
        source="sensor",
        device_id=reading.device_id,
        temperature_c=reading.temperature_c,
        humidity_pct=reading.humidity_pct,
        pressure_hpa=reading.pressure_hpa,
        payload=payload,
    )


@app.post("/fallback-readings", status_code=202)
def receive_fallback_reading(reading: FallbackWeatherReading):
    return store_reading(
        source="openweather",
        device_id=reading.location,
        temperature_c=reading.temperature_c,
        humidity_pct=reading.humidity_pct,
        pressure_hpa=reading.pressure_hpa,
        payload=reading.model_dump(),
    )