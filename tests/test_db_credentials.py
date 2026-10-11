import json

import pytest

from src.collector import db_credentials
from src.collector.config import Settings
from src.collector.db_credentials import (
    CACHE_TTL_SECONDS,
    DbCredentials,
    clear_credentials_cache,
    get_db_credentials,
)


def make_settings(db_secret_arn: str | None) -> Settings:
    return Settings(
        aws_region="eu-central-1",
        localstack_endpoint=None,
        raw_bucket="weather-raw",
        postgres_host="localhost",
        postgres_port="5433",
        postgres_db="weather",
        postgres_user="local-user",
        postgres_password="local-password",
        db_secret_arn=db_secret_arn,
        fallback_threshold_seconds=120,
        fallback_check_interval_seconds=60,
    )


@pytest.fixture(autouse=True)
def isolated_cache():
    clear_credentials_cache()
    yield
    clear_credentials_cache()


class FakeSecretsManager:
    def __init__(self, password: str = "secret-1"):
        self.password = password
        self.calls = 0

    def get_secret_value(self, SecretId):
        self.calls += 1
        return {
            "SecretString": json.dumps(
                {"username": "weather_admin", "password": self.password}
            )
        }


def install_fake_secrets_manager(monkeypatch, fake: FakeSecretsManager) -> None:
    class FakeBoto3:
        @staticmethod
        def client(service_name):
            assert service_name == "secretsmanager"
            return fake

    monkeypatch.setitem(__import__("sys").modules, "boto3", FakeBoto3)


def test_without_secret_arn_uses_local_environment_values():
    credentials = get_db_credentials(make_settings(None))

    assert credentials == DbCredentials(user="local-user", password="local-password")


def test_secret_is_read_from_secrets_manager(monkeypatch):
    fake = FakeSecretsManager()
    install_fake_secrets_manager(monkeypatch, fake)

    credentials = get_db_credentials(make_settings("arn:secret"))

    assert credentials.user == "weather_admin"
    assert credentials.password == "secret-1"
    assert fake.calls == 1


def test_secret_is_cached_until_ttl_expires(monkeypatch):
    fake = FakeSecretsManager()
    install_fake_secrets_manager(monkeypatch, fake)
    now = [1000.0]
    monkeypatch.setattr(db_credentials, "_clock", lambda: now[0])
    settings = make_settings("arn:secret")

    get_db_credentials(settings)
    now[0] += CACHE_TTL_SECONDS - 1
    get_db_credentials(settings)
    assert fake.calls == 1

    now[0] += 2
    get_db_credentials(settings)
    assert fake.calls == 2


def test_force_refresh_bypasses_the_cache(monkeypatch):
    fake = FakeSecretsManager()
    install_fake_secrets_manager(monkeypatch, fake)
    settings = make_settings("arn:secret")

    get_db_credentials(settings)
    fake.password = "secret-2"
    refreshed = get_db_credentials(settings, force_refresh=True)

    assert refreshed.password == "secret-2"
    assert get_db_credentials(settings).password == "secret-2"
    assert fake.calls == 2


def test_password_is_not_part_of_the_repr():
    credentials = DbCredentials(user="weather_admin", password="very-secret")

    assert "very-secret" not in repr(credentials)
