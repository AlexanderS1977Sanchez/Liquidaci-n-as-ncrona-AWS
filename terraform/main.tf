provider "aws" {
  region = var.aws_region

  # Punto 4: Etiquetas globales aplicadas a toda la infraestructura
  default_tags {
    tags = {
      Project     = "Agrolink"
      Environment = var.environment
      Owner       = "Jorge Sanchez"
    }
  }
}

# 1. Obtener el rol preexistente LabRole de AWS Academy
data "aws_iam_role" "lab_role" {
  name = "LabRole"
}

# 2. Base de datos DynamoDB para persistencia e idempotencia
resource "aws_dynamodb_table" "liquidaciones" {
  name         = "agrolink-liquidaciones-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id_liquidacion"

  attribute {
    name = "id_liquidacion"
    type = "S"
  }
}

# 3. Cola SQS para Dead Letter Queue (DLQ) de mensajes fallidos
resource "aws_sqs_queue" "dlq" {
  name                      = "agrolink-dlq-${var.environment}"
  message_retention_seconds = 86400
}

# 4. Cola SQS Principal
resource "aws_sqs_queue" "main_queue" {
  name                       = "agrolink-queue-${var.environment}"
  visibility_timeout_seconds = 30
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

# 5. Paquetes ZIP para las Lambdas
data "archive_file" "producer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/producer_lambda"
  output_path = "${path.module}/producer.zip"
}

data "archive_file" "consumer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/consumer_lambda"
  output_path = "${path.module}/consumer.zip"
}

# 6. Lambda Publicadora (Producer)
resource "aws_lambda_function" "producer" {
  filename         = data.archive_file.producer_zip.output_path
  function_name    = "agrolink-producer-${var.environment}"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  source_code_hash = data.archive_file.producer_zip.output_base64sha256

  environment {
    variables = {
      QUEUE_URL = aws_sqs_queue.main_queue.url
    }
  }
}

# 7. Lambda Consumidora (Consumer)
resource "aws_lambda_function" "consumer" {
  filename         = data.archive_file.consumer_zip.output_path
  function_name    = "agrolink-consumer-${var.environment}"
  role             = data.aws_iam_role.lab_role.arn
  handler          = "index.handler"
  runtime          = "nodejs18.x"
  source_code_hash = data.archive_file.consumer_zip.output_base64sha256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.liquidaciones.name
    }
  }
}

# 8. Trigger: Conectar SQS con la Lambda Consumidora
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.main_queue.arn
  function_name    = aws_lambda_function.consumer.arn
  batch_size       = 1
}

# 9. API Gateway (HTTP API) con CORS habilitado para el Front-end
resource "aws_apigatewayv2_api" "http_api" {
  name          = "agrolink-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST", "OPTIONS", "GET"]
    allow_headers = ["content-type", "x-amz-date", "authorization", "x-api-key", "x-amz-security-token"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.producer.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "post_route" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "POST /liquidaciones"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

# Permiso para que API Gateway invoque a la Lambda Producer
resource "aws_lambda_permission" "api_gw" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.producer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
}

# 10. Alarma de CloudWatch para la DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_messages_alarm" {
  alarm_name          = "agrolink-dlq-messages-alarm"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = "1"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "Alarma: Hay mensajes retenidos en la DLQ debido a errores de procesamiento."

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name 
  }
}