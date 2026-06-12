from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    aws_region: str
    localstack_endpoint: str | None
    raw_bucket: str

    postgres_host: str
    postgres_port: str
    postgres_db: str
    postgres_user: str
    postgres_password: str

    fallback_threshold_seconds: int
    fallback_check_interval_seconds: int


def optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value


def load_settings() -> Settings:
    return Settings(
        aws_region=os.getenv("AWS_DEFAULT_REGION", "eu-central-1"),
        localstack_endpoint=optional_env("LOCALSTACK_ENDPOINT"),
        raw_bucket=os.getenv("RAW_BUCKET", "weather-raw"),

        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=os.getenv("POSTGRES_PORT", "5433"),
        postgres_db=os.getenv("POSTGRES_DB", "weather"),
        postgres_user=os.getenv("POSTGRES_USER", "weather"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "weather"),

        fallback_threshold_seconds=int(os.getenv("FALLBACK_THRESHOLD_SECONDS", "120")),
        fallback_check_interval_seconds=int(os.getenv("FALLBACK_CHECK_INTERVAL_SECONDS", "60")),
    )


@lru_cache
def get_settings() -> Settings:
    return load_settings()
