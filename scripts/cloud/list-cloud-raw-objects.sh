#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -z "${AWS_PROFILE:-}" ]; then
  echo "AWS_PROFILE ist nicht gesetzt."
  echo "Beispiel:"
  echo "  export AWS_PROFILE=iot-dev"
  exit 1
fi

BUCKET_NAME="${CLOUD_RAW_BUCKET:-}"

if [ -z "$BUCKET_NAME" ]; then
  BUCKET_NAME="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw raw_bucket_name)"
fi

echo "AWS identity:"
aws sts get-caller-identity --profile "$AWS_PROFILE"
echo

echo "Bucket:"
echo "$BUCKET_NAME"
echo

aws s3 ls "s3://$BUCKET_NAME/raw_readings/" --recursive --profile "$AWS_PROFILE" | tail -20