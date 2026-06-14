variable "aws_region" {
  description = "AWS region for bootstrap infrastructure."
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used for bootstrap resources."
  type        = string
  default     = "iot-wetterdaten-pipeline"
}

variable "environment" {
  description = "Bootstrap environment name."
  type        = string
  default     = "bootstrap"
}

variable "state_bucket_name" {
  description = "Globally unique S3 bucket name for Terraform remote state."
  type        = string
}

variable "app_environment" {
  description = "Application environment managed by this bootstrap stack."
  type        = string
  default     = "dev"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the deployment role."
  type        = string
  default     = "Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline"
}

variable "github_branch" {
  description = "GitHub branch allowed to assume the deployment role."
  type        = string
  default     = "main"
}

variable "monthly_budget_limit_usd" {
  description = "Monthly AWS budget limit for this dev account/project."
  type        = string
  default     = "10"
}

variable "budget_alert_email" {
  description = "Email address for AWS Budget alerts."
  type        = string
}

variable "enable_sensor_domain" {
  description = "Whether to create a stable custom domain for sensor ingestion."
  type        = bool
  default     = false
}

variable "sensor_domain_name" {
  description = "Stable custom domain for sensor ingestion, for example sensor-domain-jakob.click."
  type        = string
  default     = ""
}