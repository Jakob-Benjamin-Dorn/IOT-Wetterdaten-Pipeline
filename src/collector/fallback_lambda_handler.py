import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_HEADER_NAME = "X-Collector-Token"


def json_response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(body),
    }


def required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def http_json(method: str, url: str, *, token: str | None = None, body: dict | None = None) -> dict:
    headers = {
        "content-type": "application/json",
    }

    if token:
        headers[TOKEN_HEADER_NAME] = token

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = Request(url=url, method=method, headers=headers, data=data)

    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def get_latest_sensor_reading(collector_api_endpoint: str, collector_token: str) -> dict | None:
    url = f"{collector_api_endpoint}/latest-readings?source=sensor&limit=1"
    data = http_json("GET", url, token=collector_token)

    readings = data.get("readings", [])
    if not readings:
        return None

    return readings[0]


def should_use_fallback(latest_sensor_reading: dict | None, threshold_seconds: int) -> tuple[bool, str]:
    if latest_sensor_reading is None:
        return True, "kein Sensorwert vorhanden"

    received_at = parse_timestamp(latest_sensor_reading["received_at"])
    age_seconds = (datetime.now(timezone.utc) - received_at).total_seconds()

    if age_seconds >= threshold_seconds:
        return True, f"letzter Sensorwert ist {age_seconds:.0f}s alt"

    return False, f"Sensorwert ist aktuell ({age_seconds:.0f}s alt)"


def fetch_openweather() -> dict:
    api_key = required_env("OPENWEATHER_API_KEY")
    lat = required_env("OPENWEATHER_LAT")
    lon = required_env("OPENWEATHER_LON")

    query = urlencode(
        {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
        }
    )

    url = f"https://api.openweathermap.org/data/2.5/weather?{query}"
    return http_json("GET", url)


def build_fallback_payload(openweather_response: dict) -> dict:
    main = openweather_response["main"]

    return {
        "temperature_c": float(main["temp"]),
        "humidity_pct": float(main["humidity"]),
        "pressure_hpa": float(main["pressure"]),
        "location": os.getenv("OPENWEATHER_LOCATION", "openweather-reference"),
        "openweather_raw": openweather_response,
    }


def lambda_handler(event, context):
    try:
        collector_api_endpoint = required_env("COLLECTOR_API_ENDPOINT").rstrip("/")
        collector_token = required_env("COLLECTOR_TOKEN")
        threshold_seconds = int(os.getenv("FALLBACK_THRESHOLD_SECONDS", "600"))

        latest_sensor_reading = get_latest_sensor_reading(
            collector_api_endpoint=collector_api_endpoint,
            collector_token=collector_token,
        )

        use_fallback, reason = should_use_fallback(
            latest_sensor_reading,
            threshold_seconds=threshold_seconds,
        )

        if not use_fallback:
            return json_response(
                200,
                {
                    "status": "skipped",
                    "reason": reason,
                    "latest_sensor_reading": latest_sensor_reading,
                },
            )

        openweather_response = fetch_openweather()
        fallback_payload = build_fallback_payload(openweather_response)

        collector_response = http_json(
            "POST",
            f"{collector_api_endpoint}/fallback-readings",
            token=collector_token,
            body=fallback_payload,
        )

        return json_response(
            202,
            {
                "status": "fallback_written",
                "reason": reason,
                "collector_response": collector_response,
            },
        )

    except Exception as exc:
        return json_response(
            500,
            {
                "status": "error",
                "detail": str(exc),
            },
        )
