#!/usr/bin/env bash
set -euo pipefail

ENDPOINT="${LOCALSTACK_ENDPOINT:-http://localhost:4566}"
BUCKET="${RAW_BUCKET:-weather-raw}"

AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}" \
AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}" \
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-eu-central-1}" \
aws --endpoint-url="$ENDPOINT" s3 ls "s3://$BUCKET" --recursive | tail -20
