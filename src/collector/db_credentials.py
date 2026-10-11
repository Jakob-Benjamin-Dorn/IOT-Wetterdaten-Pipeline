import json
import time
from dataclasses import dataclass, field

from src.collector.config import Settings

CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class DbCredentials:
    user: str
    password: str = field(repr=False)


_clock = time.monotonic
_cache: dict[str, tuple[float, DbCredentials]] = {}


def fetch_credentials_from_secret(secret_arn: str) -> DbCredentials:
    import boto3

    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    payload = json.loads(response["SecretString"])

    return DbCredentials(user=payload["username"], password=payload["password"])


def get_db_credentials(settings: Settings, *, force_refresh: bool = False) -> DbCredentials:
    """Return the database credentials.

    Cloud: read from the RDS-managed Secrets Manager secret (DB_SECRET_ARN).
    The result is cached for a few minutes, because RDS rotates the password
    regularly and a fresh Lambda container should not call Secrets Manager on
    every invocation.

    Local: use POSTGRES_USER / POSTGRES_PASSWORD from the environment.
    """
    if not settings.db_secret_arn:
        return DbCredentials(
            user=settings.postgres_user,
            password=settings.postgres_password,
        )

    cached = _cache.get(settings.db_secret_arn)
    if cached is not None and not force_refresh:
        fetched_at, credentials = cached
        if _clock() - fetched_at < CACHE_TTL_SECONDS:
            return credentials

    credentials = fetch_credentials_from_secret(settings.db_secret_arn)
    _cache[settings.db_secret_arn] = (_clock(), credentials)

    return credentials


def clear_credentials_cache() -> None:
    _cache.clear()
