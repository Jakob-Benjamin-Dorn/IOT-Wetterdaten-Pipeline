#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

AWS_PROFILE="${AWS_PROFILE:-iot-dev}"
LOCAL_PORT="${LOCAL_PORT:-3001}"
REMOTE_PORT="${REMOTE_PORT:-3000}"

INSTANCE_ID="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw grafana_instance_id)"

echo "Grafana instance: $INSTANCE_ID"
echo "Waiting for SSM agent..."

for attempt in {1..30}; do
  PING_STATUS="$(aws ssm describe-instance-information \
    --profile "$AWS_PROFILE" \
    --filters "Key=InstanceIds,Values=$INSTANCE_ID" \
    --query 'InstanceInformationList[0].PingStatus' \
    --output text 2>/dev/null || true)"

  if [ "$PING_STATUS" = "Online" ]; then
    echo "SSM status: Online"
    break
  fi

  echo "SSM status: ${PING_STATUS:-not-ready}; retrying..."
  sleep 10
done

echo
echo "Open in browser:"
echo "  http://localhost:${LOCAL_PORT}"
echo

aws ssm start-session \
  --target "$INSTANCE_ID" \
  --document-name AWS-StartPortForwardingSession \
  --parameters "{\"portNumber\":[\"${REMOTE_PORT}\"],\"localPortNumber\":[\"${LOCAL_PORT}\"]}" \
  --profile "$AWS_PROFILE"
