data "aws_route53_zone" "sensor_domain" {
  count = var.enable_sensor_domain ? 1 : 0

  name         = var.sensor_domain_name
  private_zone = false
}

resource "aws_acm_certificate" "sensor_api" {
  count = var.enable_sensor_domain ? 1 : 0

  domain_name = var.sensor_domain_name

  subject_alternative_names = [
    "*.${var.sensor_domain_name}"
  ]

  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
    prevent_destroy       = true
  }

  tags = merge(local.common_tags, {
    Name = var.sensor_domain_name
  })
}

resource "aws_route53_record" "sensor_api_validation" {
  for_each = var.enable_sensor_domain ? {
    for dvo in aws_acm_certificate.sensor_api[0].domain_validation_options :
    dvo.domain_name => {
      name   = dvo.resource_record_name
      type   = dvo.resource_record_type
      record = dvo.resource_record_value
    }
  } : {}

  allow_overwrite = true
  zone_id         = data.aws_route53_zone.sensor_domain[0].zone_id
  name            = each.value.name
  type            = each.value.type
  ttl             = 60
  records         = [each.value.record]
}

resource "aws_acm_certificate_validation" "sensor_api" {
  count = var.enable_sensor_domain ? 1 : 0

  certificate_arn         = aws_acm_certificate.sensor_api[0].arn
  validation_record_fqdns = [for record in aws_route53_record.sensor_api_validation : record.fqdn]
}

resource "aws_apigatewayv2_domain_name" "sensor_api" {
  count = var.enable_sensor_domain ? 1 : 0

  domain_name = var.sensor_domain_name

  domain_name_configuration {
    certificate_arn = aws_acm_certificate_validation.sensor_api[0].certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }

  tags = merge(local.common_tags, {
    Name = var.sensor_domain_name
  })
}

resource "aws_route53_record" "sensor_api_alias" {
  count = var.enable_sensor_domain ? 1 : 0

  zone_id = data.aws_route53_zone.sensor_domain[0].zone_id
  name    = var.sensor_domain_name
  type    = "A"

  alias {
    name                   = aws_apigatewayv2_domain_name.sensor_api[0].domain_name_configuration[0].target_domain_name
    zone_id                = aws_apigatewayv2_domain_name.sensor_api[0].domain_name_configuration[0].hosted_zone_id
    evaluate_target_health = false
  }
}
