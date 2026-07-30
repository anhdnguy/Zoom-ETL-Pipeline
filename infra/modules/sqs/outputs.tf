output "queue_url" {
  description = "SQS Queue URL"
  value       = aws_sqs_queue.main.url
}

output "queue_arn" {
  description = "SQS Queue ARN"
  value       = aws_sqs_queue.main.arn
}

output "queue_name" {
  description = "SQS Queue name"
  value       = aws_sqs_queue.main.name
}

output "queue_id" {
  description = "SQS Queue ID"
  value       = aws_sqs_queue.main.id
}

output "dlq_url" {
  description = "Dead Letter Queue URL"
  value       = aws_sqs_queue.dlq.url
}

output "dlq_arn" {
  description = "Dead Letter Queue ARN"
  value       = aws_sqs_queue.dlq.arn
}

output "dlq_name" {
  description = "Dead Letter Queue name"
  value       = aws_sqs_queue.dlq.name
}