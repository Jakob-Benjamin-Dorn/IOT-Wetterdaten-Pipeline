output "raw_bucket_name" {
  description = "Name of the S3 bucket for raw weather payloads."
  value       = aws_s3_bucket.raw_weather_data.bucket
}

output "raw_bucket_arn" {
  description = "ARN of the S3 bucket for raw weather payloads."
  value       = aws_s3_bucket.raw_weather_data.arn
}
