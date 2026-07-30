# =============================================================================
# SQS MODULE
# Purpose: Sending jobs to ECS for downloading
# =============================================================================

# Dead Letter Queue (DLQ) for failed messages
resource "aws_sqs_queue" "dlq" {
  name                      = "${var.environment}-${var.project_name}-recording-dlq"
  message_retention_seconds = 1209600 # 14 days (maximum)

  tags = {
    Name        = "${var.project_name}-${var.environment}-recording-dlq"
    Description = "Queue for recording download jobs"
  }
}

# Main SQS Queue for recording download jobs
resource "aws_sqs_queue" "main" {
  name                       = "${var.project_name}-${var.environment}-recording-queue"
  delay_seconds              = 0
  max_message_size           = 262144 # 256 KB (maximum)
  message_retention_seconds  = 345600 # 4 days
  receive_wait_time_seconds  = 20     # Long polling (max 20 seconds)
  visibility_timeout_seconds = 3600   # 1 hour (for large file downloads)

  # Redrive policy - send to DLQ after 3 failed attempts
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-recording-queue"
    Description = "Queue for recording download jobs"
  }
}

# SQS Queue Policy (allow Lambda and services to send messages)
resource "aws_sqs_queue_policy" "main" {
  queue_url = aws_sqs_queue.main.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowLambdaToSendMessage"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
        Action   = "sqs:SendMessage"
        Resource = aws_sqs_queue.main.arn
      },
      {
        Sid    = "AllowECSTasksToReceiveMessages"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:ChangeMessageVisibility"
        ]
        Resource = aws_sqs_queue.main.arn
      }
    ]
  })
}

# CloudWatch Alarms for Queue Monitoring

# Alarm: DLQ has messages (indicates failures)
resource "aws_cloudwatch_metric_alarm" "dlq_messages" {
  alarm_name          = "${var.project_name}-${var.environment}-dlq-messages"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = 5
  alarm_description   = "Alert when DLQ has more than 5 messages - indicates download failures"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.dlq.name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-dlq-alarm"
  }
}

# Alarm: Messages aging in queue (not being processed)
resource "aws_cloudwatch_metric_alarm" "queue_age" {
  alarm_name          = "${var.project_name}-${var.environment}-queue-age"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateAgeOfOldestMessage"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Maximum"
  threshold           = 3600 # 1 hour
  alarm_description   = "Alert when oldest message is older than 1 hour - workers may be stuck"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-queue-age-alarm"
  }
}

# Alarm: Too many messages in queue (backlog building up)
resource "aws_cloudwatch_metric_alarm" "queue_depth" {
  alarm_name          = "${var.project_name}-${var.environment}-queue-depth"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Average"
  threshold           = var.environment == "prod" ? 100 : 50
  alarm_description   = "Alert when queue has too many pending messages - may need more workers"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-queue-depth-alarm"
  }
}

# Alarm: Messages being deleted without processing (empty receives)
resource "aws_cloudwatch_metric_alarm" "empty_receives" {
  alarm_name          = "${var.project_name}-${var.environment}-empty-receives"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "NumberOfEmptyReceives"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 100
  alarm_description   = "Alert when too many empty receives - workers may be polling inefficiently"
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.main.name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-empty-receives-alarm"
  }
}