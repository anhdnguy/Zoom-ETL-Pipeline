output "function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.webhook.function_name
}

output "function_arn" {
  description = "Lambda function ARN"
  value       = aws_lambda_function.webhook.arn
}

output "function_url" {
  description = "Lambda function URL (Zoom webhook endpoint)"
  value       = aws_lambda_function_url.zoom_webhook.function_url
}

output "function_invoke_arn" {
  description = "Lambda function invoke ARN"
  value       = aws_lambda_function.webhook.invoke_arn
}

output "log_group_name" {
  description = "CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.lambda.name
}