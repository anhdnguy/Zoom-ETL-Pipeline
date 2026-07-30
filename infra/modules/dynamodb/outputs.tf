output "table_name" {
  description = "Name of the application DynamoDB table."
  value       = aws_dynamodb_table.app.name
}

output "table_arn" {
  description = "ARN of the application DynamoDB table."
  value       = aws_dynamodb_table.app.arn
}