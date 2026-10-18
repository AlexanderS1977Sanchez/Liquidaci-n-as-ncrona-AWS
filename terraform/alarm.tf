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