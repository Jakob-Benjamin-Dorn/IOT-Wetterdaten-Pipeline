locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }
}

resource "aws_s3_bucket" "raw_weather_data" {
  bucket = var.raw_bucket_name

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-raw-weather-data"
    }
  )
}

resource "aws_s3_bucket_public_access_block" "raw_weather_data" {
  bucket = aws_s3_bucket.raw_weather_data.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "raw_weather_data" {
  bucket = aws_s3_bucket.raw_weather_data.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "raw_weather_data" {
  bucket = aws_s3_bucket.raw_weather_data.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
