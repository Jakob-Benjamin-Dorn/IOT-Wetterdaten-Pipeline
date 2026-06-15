resource "aws_apigatewayv2_api_mapping" "sensor_api" {
  count = data.terraform_remote_state.bootstrap.outputs.sensor_api_domain_name == null ? 0 : 1

  api_id      = aws_apigatewayv2_api.collector.id
  domain_name = data.terraform_remote_state.bootstrap.outputs.sensor_api_domain_name
  stage       = aws_apigatewayv2_stage.collector.name
}
