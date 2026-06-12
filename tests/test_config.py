from src.collector.config import load_settings


def test_load_settings_uses_local_defaults(monkeypatch):
    monkeypatch.delenv("LOCALSTACK_ENDPOINT", raising=False)
    monkeypatch.delenv("RAW_BUCKET", raising=False)
    monkeypatch.delenv("POSTGRES_PORT", raising=False)

    settings = load_settings()

    assert settings.localstack_endpoint is None
    assert settings.raw_bucket == "weather-raw"
    assert settings.postgres_port == "5433"
    assert settings.aws_region == "eu-central-1"


def test_load_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("LOCALSTACK_ENDPOINT", "http://localhost:4566")
    monkeypatch.setenv("RAW_BUCKET", "custom-bucket")
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    monkeypatch.setenv("FALLBACK_THRESHOLD_SECONDS", "300")
    monkeypatch.setenv("FALLBACK_CHECK_INTERVAL_SECONDS", "30")

    settings = load_settings()

    assert settings.localstack_endpoint == "http://localhost:4566"
    assert settings.raw_bucket == "custom-bucket"
    assert settings.postgres_port == "15432"
    assert settings.fallback_threshold_seconds == 300
    assert settings.fallback_check_interval_seconds == 30
