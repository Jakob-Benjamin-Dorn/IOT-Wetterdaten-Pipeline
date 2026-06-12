from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from src.collector.exceptions import CollectorStorageError
from src.collector.ingestion import store_reading
from src.collector.raw_storage import ensure_bucket_exists
from src.collector.models import FallbackWeatherReading, SensorReading


app = FastAPI(title="IoT Wetterdaten Collector")


@app.on_event("startup")
def startup_event():
    ensure_bucket_exists()


@app.get("/health")
def health():
    return {"status": "ok"}


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

    print("Received payload:", payload)

    try:
        reading = SensorReading.model_validate(payload)
    except ValidationError as exc:
        print(f"Invalid sensor payload: {exc}")
        raise HTTPException(
            status_code=422,
            detail=exc.errors(),
        ) from exc

    try:
        return store_reading(
            source="sensor",
            device_id=reading.device_id,
            temperature_c=reading.temperature_c,
            humidity_pct=reading.humidity_pct,
            pressure_hpa=reading.pressure_hpa,
            payload=payload,
        )
    except CollectorStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/fallback-readings", status_code=202)
def receive_fallback_reading(reading: FallbackWeatherReading):
    try:
        return store_reading(
            source="openweather",
            device_id=reading.location,
            temperature_c=reading.temperature_c,
            humidity_pct=reading.humidity_pct,
            pressure_hpa=reading.pressure_hpa,
            payload=reading.model_dump(),
        )
    except CollectorStorageError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc