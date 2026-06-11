#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

export PYTHONPATH="$PROJECT_ROOT:${PYTHONPATH:-}"

INTERVAL_SECONDS="${FALLBACK_CHECK_INTERVAL_SECONDS:-60}"

echo "Starte lokale Fallback-Prüfung alle ${INTERVAL_SECONDS}s."
echo "Projektverzeichnis: $PROJECT_ROOT"
echo "Abbrechen mit Ctrl+C."
echo

while true; do
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Prüfe Fallback-Status..."
  python3 scripts/fallback/check-and-fetch-fallback.py
  echo
  sleep "$INTERVAL_SECONDS"
done