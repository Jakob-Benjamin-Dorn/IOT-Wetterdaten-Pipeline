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
