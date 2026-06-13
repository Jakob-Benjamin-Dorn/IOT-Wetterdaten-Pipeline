#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

AWS_PROFILE="${AWS_PROFILE:-iot-dev}"
AWS_REGION="${AWS_REGION:-eu-central-1}"
IMAGE_TAG="${IMAGE_TAG:-latest}"

ECR_REPO_URL="$(cd "$PROJECT_ROOT/infra/dev" && terraform output -raw grafana_ecr_repository_url)"

echo "AWS profile: $AWS_PROFILE"
echo "AWS region:  $AWS_REGION"
echo "ECR repo:    $ECR_REPO_URL"
echo "Image tag:   $IMAGE_TAG"
echo

aws ecr get-login-password \
  --region "$AWS_REGION" \
  --profile "$AWS_PROFILE" \
| docker login \
  --username AWS \
  --password-stdin "${ECR_REPO_URL%/*}"

docker build \
  -f "$PROJECT_ROOT/docker/grafana/Dockerfile" \
  -t "iot-wetterstation-grafana:$IMAGE_TAG" \
  "$PROJECT_ROOT"

docker tag \
  "iot-wetterstation-grafana:$IMAGE_TAG" \
  "$ECR_REPO_URL:$IMAGE_TAG"

docker push "$ECR_REPO_URL:$IMAGE_TAG"

echo
echo "Pushed:"
echo "$ECR_REPO_URL:$IMAGE_TAG"
