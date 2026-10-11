import psycopg
import pytest

from src.collector import rds_storage
from src.collector.config import Settings
from src.collector.db_credentials import DbCredentials


def make_settings(db_secret_arn: str | None) -> Settings:
    return Settings(
        aws_region="eu-central-1",
        localstack_endpoint=None,
        raw_bucket="weather-raw",
        postgres_host="db.example",
        postgres_port="5432",
        postgres_db="weather",
        postgres_user="local-user",
        postgres_password="local-password",
        db_secret_arn=db_secret_arn,
        fallback_threshold_seconds=120,
        fallback_check_interval_seconds=60,
    )


def install_credentials(monkeypatch, settings: Settings, passwords: list[str]):
    """Return the passwords one after another; record the force_refresh flags."""
    refresh_flags: list[bool] = []

    def fake_get_db_credentials(_settings, *, force_refresh=False):
        refresh_flags.append(force_refresh)
        return DbCredentials(user="weather_admin", password=passwords.pop(0))

    monkeypatch.setattr(rds_storage, "get_settings", lambda: settings)
    monkeypatch.setattr(rds_storage, "get_db_credentials", fake_get_db_credentials)

    return refresh_flags


def test_connection_kwargs_contain_the_resolved_credentials(monkeypatch):
    install_credentials(monkeypatch, make_settings("arn:secret"), ["pw"])

    kwargs = rds_storage.get_connection_kwargs()

    assert kwargs["host"] == "db.example"
    assert kwargs["user"] == "weather_admin"
    assert kwargs["password"] == "pw"


def test_connect_retries_once_with_fresh_credentials_after_rotation(monkeypatch):
    refresh_flags = install_credentials(
        monkeypatch, make_settings("arn:secret"), ["old", "new"]
    )
    used_passwords: list[str] = []

    def fake_connect(**kwargs):
        used_passwords.append(kwargs["password"])
        if kwargs["password"] == "old":
            raise psycopg.OperationalError(
                'FATAL:  password authentication failed for user "weather_admin"'
            )
        return "connection"

    monkeypatch.setattr(rds_storage.psycopg, "connect", fake_connect)

    assert rds_storage.connect() == "connection"
    assert used_passwords == ["old", "new"]
    assert refresh_flags == [False, True]


def test_connect_does_not_retry_without_secret(monkeypatch):
    install_credentials(monkeypatch, make_settings(None), ["pw", "pw"])
    attempts: list[dict] = []

    def fake_connect(**kwargs):
        attempts.append(kwargs)
        raise psycopg.OperationalError("password authentication failed")

    monkeypatch.setattr(rds_storage.psycopg, "connect", fake_connect)

    with pytest.raises(psycopg.OperationalError):
        rds_storage.connect()

    assert len(attempts) == 1


def test_connect_does_not_retry_on_other_errors(monkeypatch):
    install_credentials(monkeypatch, make_settings("arn:secret"), ["pw", "pw"])
    attempts: list[dict] = []

    def fake_connect(**kwargs):
        attempts.append(kwargs)
        raise psycopg.OperationalError("connection timed out")

    monkeypatch.setattr(rds_storage.psycopg, "connect", fake_connect)

    with pytest.raises(psycopg.OperationalError):
        rds_storage.connect()

    assert len(attempts) == 1
