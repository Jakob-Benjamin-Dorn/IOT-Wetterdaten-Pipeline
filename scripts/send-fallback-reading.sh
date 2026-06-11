#!/usr/bin/env bash
set -euo pipefail

COLLECTOR_URL="${COLLECTOR_URL:-http://localhost:8088/fallback-readings}"

curl -sS -X POST "$COLLECTOR_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "karlsruhe-gruenwinkel",
    "temperature_c": 21.8,
    "humidity_pct": 52.0,
    "pressure_hpa": 1012.4
  }'

echo
