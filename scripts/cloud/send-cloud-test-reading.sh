#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

API_URL="${COLLECTOR_API_URL:-}"
COLLECTOR_TOKEN="${COLLECTOR_TOKEN:-}"

if [ -z "$API_URL" ]; then
  API_URL="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw collector_api_endpoint)"
fi

if [ -z "$COLLECTOR_TOKEN" ]; then
  echo "COLLECTOR_TOKEN ist nicht gesetzt."
  echo "Beispiel:"
  echo "  export COLLECTOR_TOKEN=..."
  exit 1
fi

curl -i -X POST "$API_URL/sensor-readings" \
  -H "Content-Type: application/json" \
  -H "X-Collector-Token: $COLLECTOR_TOKEN" \
  -d '{
    "device_id": "cloud-smoke-test-device",
    "temperature_c": 22.8,
    "humidity_pct": 44.2,
    "pressure_hpa": 1012.9
  }'