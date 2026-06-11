#!/usr/bin/env bash
set -euo pipefail

COLLECTOR_URL="${COLLECTOR_URL:-http://localhost:8088/readings}"

curl -sS -X POST "$COLLECTOR_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test-data",
    "temperature_c": 22.5,
    "humidity_pct": 33.0,
    "pressure_hpa": 1013.2
  }'

echo
