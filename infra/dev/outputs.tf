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