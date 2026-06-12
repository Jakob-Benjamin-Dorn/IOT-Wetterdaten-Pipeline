variable "aws_region" {
  description = "AWS region for the dev environment."
  type        = string
  default     = "eu-central-1"
}

variable "project_name" {
  description = "Project name used for tags and resource names."
  type        = string
  default     = "iot-wetterdaten-pipeline"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "raw_bucket_name" {
  description = "Globally unique S3 bucket name for raw weather payloads."
  type        = string
}

variable "collector_token" {
  description = "Shared token required by the collector Lambda."
  type        = string
  sensitive   = true
}