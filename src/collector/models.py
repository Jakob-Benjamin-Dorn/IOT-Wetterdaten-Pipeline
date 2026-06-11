from pydantic import BaseModel, Field


class SensorReading(BaseModel):
    device_id: str = Field(..., min_length=1, max_length=80)
    temperature_c: float = Field(..., ge=-20, le=50)
    humidity_pct: float = Field(..., ge=0, le=100)
    pressure_hpa: float = Field(..., ge=800, le=1200)


class FallbackWeatherReading(BaseModel):
    temperature_c: float = Field(..., ge=-20, le=50)
    humidity_pct: float = Field(..., ge=0, le=100)
    pressure_hpa: float = Field(..., ge=800, le=1200)
    location: str = Field(default="openweather-reference", max_length=120)
