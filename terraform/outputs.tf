output "api_endpoint" {
  description = "URL base del API Gateway para enviar peticiones POST /liquidaciones"
  value       = aws_apigatewayv2_api.http_api.api_endpoint
}