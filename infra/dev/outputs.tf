output "raw_bucket_name" {
  description = "Name of the S3 bucket for raw weather payloads."
  value       = aws_s3_bucket.raw_weather_data.bucket
}

output "raw_bucket_arn" {
  description = "ARN of the S3 bucket for raw weather payloads."
  value       = aws_s3_bucket.raw_weather_data.arn
}

output "collector_lambda_function_name" {
  description = "Name of the collector Lambda function."
  value       = aws_lambda_function.collector.function_name
}

output "collector_lambda_arn" {
  description = "ARN of the collector Lambda function."
  value       = aws_lambda_function.collector.arn
}

output "collector_api_endpoint" {
  description = "HTTP API endpoint for the collector."
  value       = aws_apigatewayv2_api.collector.api_endpoint
}

output "postgres_endpoint" {
  description = "RDS PostgreSQL endpoint."
  value       = aws_db_instance.postgres.address
}

output "postgres_database" {
  description = "RDS PostgreSQL database name."
  value       = aws_db_instance.postgres.db_name
}

output "postgres_username" {
  description = "RDS PostgreSQL username."
  value       = aws_db_instance.postgres.username
}

output "grafana_instance_id" {
  description = "EC2 instance ID for the private Grafana instance."
  value       = aws_instance.grafana.id
}

output "grafana_ssm_port_forward_command" {
  description = "Command to open Grafana locally through SSM port forwarding."
  value       = "aws ssm start-session --target ${aws_instance.grafana.id} --document-name AWS-StartPortForwardingSession --parameters '{\"portNumber\":[\"3000\"],\"localPortNumber\":[\"3000\"]}' --profile iot-dev"
}

output "grafana_ecr_repository_url" {
  description = "ECR repository URL for the Grafana image."
  value       = data.terraform_remote_state.bootstrap.outputs.grafana_ecr_repository_url
}

output "fallback_lambda_function_name" {
  description = "Name of the cloud fallback Lambda function."
  value       = aws_lambda_function.fallback.function_name
}

output "fallback_schedule_name" {
  description = "Name of the EventBridge Scheduler schedule for cloud fallback checks."
  value       = aws_scheduler_schedule.fallback_check.name
}

output "github_actions_grafana_role_arn" {
  description = "IAM role ARN assumed by GitHub Actions to build, push and restart Grafana."
  value       = data.terraform_remote_state.bootstrap.outputs.github_actions_grafana_role_arn
}

output "stable_sensor_api_url" {
  description = "Stable custom domain URL for sensor ingestion."
  value       = data.terraform_remote_state.bootstrap.outputs.sensor_api_url
}