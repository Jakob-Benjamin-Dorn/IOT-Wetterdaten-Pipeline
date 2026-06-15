#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

API_URL="${COLLECTOR_API_URL:-}"
COLLECTOR_TOKEN="${COLLECTOR_TOKEN:-}"

if [ -z "$API_URL" ]; then
  API_URL="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw stable_sensor_api_url 2>/dev/null || true)"
fi

if [ -z "$API_URL" ] || [ "$API_URL" = "null" ]; then
  API_URL="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw collector_api_endpoint)"
fi

if [ -z "$COLLECTOR_TOKEN" ]; then
  echo "COLLECTOR_TOKEN ist nicht gesetzt."
  echo "Beispiel:"
  echo "  export COLLECTOR_TOKEN=..."
  exit 1
fi

curl -sS -X GET "$API_URL/latest-readings" \
  -H "X-Collector-Token: $COLLECTOR_TOKEN" | python3 -m json.tool
