#!/usr/bin/env bash
set -euo pipefail

COLLECTOR_URL="${COLLECTOR_URL:-http://localhost:8088}"

echo "1/4 Prüfe Collector Health Check..."
curl -fsS "$COLLECTOR_URL/health"
echo
echo

echo "2/4 Sende Testmessung..."
curl -fsS -X POST "$COLLECTOR_URL/sensor-readings" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "smoke-test-device",
    "temperature_c": 22.5,
    "humidity_pct": 45.0,
    "pressure_hpa": 1013.2
  }'
echo
echo

echo "3/4 Prüfe PostgreSQL..."
docker exec -i wetter-postgres psql -U weather -d weather -c "
SELECT
  id,
  source,
  device_id,
  received_at,
  temperature_c,
  humidity_pct,
  pressure_hpa
FROM weather_readings
ORDER BY id DESC
LIMIT 5;
"
echo

echo "4/4 Prüfe LocalStack S3..."
ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
BUCKET="${RAW_BUCKET:-weather-raw}"

AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}" \
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}" \
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-central-1}" \
aws --endpoint-url="$ENDPOINT" s3 ls "s3://$BUCKET" --recursive | tail -10

echo
echo "Smoke-Test abgeschlossen."
