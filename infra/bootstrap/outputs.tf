output "terraform_state_bucket_name" {
  description = "S3 bucket used for Terraform remote state."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "terraform_state_bucket_arn" {
  description = "ARN of the S3 bucket used for Terraform remote state."
  value       = aws_s3_bucket.terraform_state.arn
}

output "aws_account_id" {
  description = "AWS account ID used for bootstrap."
  value       = data.aws_caller_identity.current.account_id
}

output "grafana_ecr_repository_url" {
  description = "ECR repository URL for the Grafana image."
  value       = aws_ecr_repository.grafana.repository_url
}

output "grafana_ecr_repository_arn" {
  description = "ECR repository ARN for the Grafana image."
  value       = aws_ecr_repository.grafana.arn
}

output "github_actions_grafana_role_arn" {
  description = "IAM role ARN assumed by GitHub Actions to build, push and restart Grafana."
  value       = aws_iam_role.github_actions_grafana_deploy.arn
}

output "monthly_budget_name" {
  description = "Name of the monthly AWS budget."
  value       = aws_budgets_budget.monthly_dev_cost.name
}

output "sensor_api_domain_name" {
  description = "Stable sensor API custom domain name."
  value       = var.enable_sensor_domain ? aws_apigatewayv2_domain_name.sensor_api[0].domain_name : null
}

output "sensor_api_url" {
  description = "Stable sensor API base URL."
  value       = var.enable_sensor_domain ? "https://${var.sensor_domain_name}" : null
}

output "sensor_hosted_zone_id" {
  description = "Route53 hosted zone ID for the sensor domain."
  value       = var.enable_sensor_domain ? data.aws_route53_zone.sensor_domain[0].zone_id : null
}