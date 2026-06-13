locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  lambda_package_path = "${path.module}/../../build/lambda/collector-lambda.zip"
}

resource "aws_s3_bucket" "raw_weather_data" {
  bucket        = var.raw_bucket_name
  force_destroy = true

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

data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "dev" {
  cidr_block           = "10.20.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-vpc"
    }
  )
}

resource "aws_subnet" "private_a" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = "10.20.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-private-a"
    }
  )
}

resource "aws_subnet" "private_b" {
  vpc_id            = aws_vpc.dev.id
  cidr_block        = "10.20.2.0/24"
  availability_zone = data.aws_availability_zones.available.names[1]

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-private-b"
    }
  )
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.dev.id

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-private-rt"
    }
  )
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.dev.id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private.id]

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-s3-endpoint"
    }
  )
}

resource "aws_security_group" "lambda" {
  name        = "${var.project_name}-${var.environment}-lambda-sg"
  description = "Security group for collector Lambda"
  vpc_id      = aws_vpc.dev.id

  egress {
    description = "Allow outbound traffic from Lambda"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_security_group" "rds" {
  name        = "${var.project_name}-${var.environment}-rds-sg"
  description = "Security group for PostgreSQL RDS"
  vpc_id      = aws_vpc.dev.id

  ingress {
    description     = "Allow PostgreSQL from Lambda"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda.id]
  }

  tags = local.common_tags
}

resource "aws_db_subnet_group" "postgres" {
  name = "${var.project_name}-${var.environment}-postgres-subnets"

  subnet_ids = [
    aws_subnet.private_a.id,
    aws_subnet.private_b.id,
  ]

  tags = local.common_tags
}

resource "aws_db_instance" "postgres" {
  identifier = "${var.project_name}-${var.environment}-postgres"

  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t4g.micro"

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.postgres.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  backup_retention_period = 0
  skip_final_snapshot     = true
  deletion_protection     = false

  apply_immediately = true

  tags = merge(
    local.common_tags,
    {
      Name = "${var.project_name}-${var.environment}-postgres"
    }
  )
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

  vpc_config {
    subnet_ids = [
      aws_subnet.private_a.id,
      aws_subnet.private_b.id,
    ]

    security_group_ids = [
      aws_security_group.lambda.id,
    ]
  }

  environment {
    variables = {
      RAW_BUCKET      = aws_s3_bucket.raw_weather_data.bucket
      COLLECTOR_TOKEN = var.collector_token

      POSTGRES_HOST     = aws_db_instance.postgres.address
      POSTGRES_PORT     = "5432"
      POSTGRES_DB       = var.db_name
      POSTGRES_USER     = var.db_username
      POSTGRES_PASSWORD = var.db_password
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.collector_lambda_basic_execution,
    aws_iam_role_policy_attachment.collector_lambda_vpc_access,
    aws_iam_role_policy.collector_lambda_s3_write
  ]

  tags = local.common_tags
}

resource "aws_iam_role_policy_attachment" "collector_lambda_vpc_access" {
  role       = aws_iam_role.collector_lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
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

resource "aws_apigatewayv2_route" "latest_readings" {
  api_id    = aws_apigatewayv2_api.collector.id
  route_key = "GET /latest-readings"
  target    = "integrations/${aws_apigatewayv2_integration.collector_lambda.id}"
}
