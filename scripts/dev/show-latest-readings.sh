#!/usr/bin/env bash
set -euo pipefail

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
LIMIT 15;
"
