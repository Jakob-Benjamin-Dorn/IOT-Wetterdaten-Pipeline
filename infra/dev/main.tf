locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  lambda_package_path = "${path.module}/../../build/lambda/collector-lambda.zip"
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

resource "aws_iam_role" "collector_lambda" {
  name = "${var.project_name}-${var.environment}-collector-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "collector_lambda_basic_execution" {
  role       = aws_iam_role.collector_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "collector_lambda_s3_write" {
  name = "${var.project_name}-${var.environment}-collector-s3-write"
  role = aws_iam_role.collector_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject"
        ]
        Resource = "${aws_s3_bucket.raw_weather_data.arn}/raw_readings/*"
      }
    ]
  })
}

resource "aws_lambda_function" "collector" {
  function_name = "${var.project_name}-${var.environment}-collector"
  role          = aws_iam_role.collector_lambda.arn
  runtime       = "python3.13"
  handler       = "src.collector.lambda_handler.lambda_handler"

  filename         = local.lambda_package_path
  source_code_hash = filebase64sha256(local.lambda_package_path)

  memory_size = 128
  timeout     = 10

  environment {
    variables = {
      RAW_BUCKET = aws_s3_bucket.raw_weather_data.bucket
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.collector_lambda_basic_execution,
    aws_iam_role_policy.collector_lambda_s3_write
  ]

  tags = local.common_tags
}

resource "aws_apigatewayv2_api" "collector" {
  name          = "${var.project_name}-${var.environment}-collector-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_headers = ["content-type"]
    allow_methods = ["POST", "OPTIONS"]
    allow_origins = ["*"]
  }

  tags = local.common_tags
}

resource "aws_apigatewayv2_integration" "collector_lambda" {
  api_id                 = aws_apigatewayv2_api.collector.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.collector.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "sensor_readings" {
  api_id    = aws_apigatewayv2_api.collector.id
  route_key = "POST /sensor-readings"
  target    = "integrations/${aws_apigatewayv2_integration.collector_lambda.id}"
}

resource "aws_apigatewayv2_stage" "dev" {
  api_id      = aws_apigatewayv2_api.collector.id
  name        = "$default"
  auto_deploy = true

  tags = local.common_tags
}

resource "aws_lambda_permission" "allow_api_gateway" {
  statement_id  = "AllowApiGatewayInvokeCollector"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.collector.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.collector.execution_arn}/*/*"
}
