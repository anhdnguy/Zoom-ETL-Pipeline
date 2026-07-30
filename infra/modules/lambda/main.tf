# =============================================================================
# LAMBDA MODULE
# Purpose: Recording webhook handler - validates, transforms, sends to SQS
# =============================================================================

# Lambda Function
resource "aws_lambda_function" "webhook" {
  filename      = var.lambda_source_dir
  function_name = "${var.project_name}-${var.environment}-zoom-webhook"
  role          = var.lambda_role_arn
  handler       = var.lambda_handler
  runtime       = var.lambda_runtime
  timeout       = var.lambda_timeout
  memory_size   = var.lambda_memory_size

  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [var.lambda_security_group_id]
  }

  environment {
    variables = {
      PROJECT_NAME  = var.project_name
      ENVIRONMENT   = var.environment
      SQS_QUEUE_URL = var.sqs_queue_url
      SECRET_NAME   = var.secret_name
      LOG_LEVEL     = var.environment == "prod" ? "INFO" : "DEBUG"
      REGION        = var.region
      BUCKET_NAME   = var.datalake_bucket_name
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-zoom-recording-webhook"
  }
}

# Lambda Function URL (for Zoom webhook endpoint)
resource "aws_lambda_function_url" "zoom_webhook" {
  function_name      = aws_lambda_function.webhook.function_name
  authorization_type = "NONE" # Zoom webhooks don't support AWS IAM auth

  cors {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type", "x-zm-signature", "x-zm-request-timestamp"]
    max_age       = 86400
  }
}

# Lambda permission to allow public invocation via Function URL
resource "aws_lambda_permission" "allow_function_url" {
  statement_id           = "AllowFunctionURLInvoke"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.webhook.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${aws_lambda_function.webhook.function_name}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-logs"
  }
}

# CloudWatch Alarms for Lambda Monitoring

# Alarm: High error rate
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Alert when Lambda has more than 5 errors in 10 minutes"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.webhook.function_name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-errors-alarm"
  }
}

# Alarm: High invocation duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 10000 # 10 seconds
  alarm_description   = "Alert when Lambda average duration exceeds 10 seconds"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.webhook.function_name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-duration-alarm"
  }
}

# Alarm: Throttling
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when Lambda is throttled"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.webhook.function_name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-throttles-alarm"
  }
}

# Alarm: Concurrent executions approaching limit
resource "aws_cloudwatch_metric_alarm" "lambda_concurrent_executions" {
  alarm_name          = "${var.project_name}-${var.environment}-lambda-concurrent"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ConcurrentExecutions"
  namespace           = "AWS/Lambda"
  period              = 60
  statistic           = "Maximum"
  threshold           = var.environment == "prod" ? 8 : 4
  alarm_description   = "Alert when concurrent executions approach reserved limit"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.webhook.function_name
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-lambda-concurrent-alarm"
  }
}