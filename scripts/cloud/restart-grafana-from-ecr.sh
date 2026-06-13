#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

AWS_PROFILE="${AWS_PROFILE:-iot-dev}"
AWS_REGION="${AWS_REGION:-eu-central-1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

INSTANCE_ID="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw grafana_instance_id)"
ECR_REPO_URL="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw grafana_ecr_repository_url)"
ECR_REGISTRY="${ECR_REPO_URL%/*}"
IMAGE_URI="${ECR_REPO_URL}:${IMAGE_TAG}"

echo "Instance: $INSTANCE_ID"
echo "Image:    $IMAGE_URI"
echo

COMMANDS=$(cat <<EOF
[
  "set -euxo pipefail",
  "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${ECR_REGISTRY}",
  "docker pull ${IMAGE_URI}",
  "/opt/grafana/run-grafana.sh ${IMAGE_URI}",
  "sleep 10",
  "curl -f http://127.0.0.1:3000/api/health"
]
EOF
)

COMMAND_ID="$(aws ssm send-command \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --instance-ids "$INSTANCE_ID" \
  --document-name "AWS-RunShellScript" \
  --comment "Restart Grafana from ECR image" \
  --parameters "commands=$COMMANDS" \
  --query "Command.CommandId" \
  --output text)"

echo "Command ID: $COMMAND_ID"
echo "Waiting for command to finish..."

aws ssm wait command-executed \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID"

aws ssm get-command-invocation \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --command-id "$COMMAND_ID" \
  --instance-id "$INSTANCE_ID" \
  --query '{Status:Status,Stdout:StandardOutputContent,Stderr:StandardErrorContent}' \
  --output json