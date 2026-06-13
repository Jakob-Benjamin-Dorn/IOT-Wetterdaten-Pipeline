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

variable "db_name" {
  description = "PostgreSQL database name."
  type        = string
  default     = "weather"
}

variable "db_username" {
  description = "PostgreSQL admin username."
  type        = string
  default     = "weather"
}

variable "db_password" {
  description = "PostgreSQL admin password."
  type        = string
  sensitive   = true
}

variable "grafana_admin_password" {
  description = "Admin password for the dev Grafana instance."
  type        = string
  sensitive   = true
}

variable "openweather_api_key" {
  description = "OpenWeather API key for the cloud fallback Lambda."
  type        = string
  sensitive   = true
}

variable "openweather_lat" {
  description = "Latitude for OpenWeather fallback."
  type        = string
}

variable "openweather_lon" {
  description = "Longitude for OpenWeather fallback."
  type        = string
}

variable "openweather_location" {
  description = "Logical device/location name for OpenWeather fallback readings."
  type        = string
  default     = "openweather-reference"
}

variable "cloud_fallback_threshold_seconds" {
  description = "Age in seconds after which OpenWeather fallback is written."
  type        = number
  default     = 600
}

variable "cloud_fallback_schedule_expression" {
  description = "EventBridge Scheduler expression for the cloud fallback check."
  type        = string
  default     = "rate(5 minutes)"
}

variable "github_repository" {
  description = "GitHub repository allowed to push the Grafana image via OIDC."
  type        = string
  default     = "Jakob-Benjamin-Dorn/IOT-Wetterdaten-Pipeline"
}

variable "github_branch" {
  description = "GitHub branch allowed to assume the deployment role."
  type        = string
  default     = "main"
}