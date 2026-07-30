output "service_name" {
  description = "Downloader ECS service name"
  value       = aws_ecs_service.downloader.name
}

output "service_id" {
  description = "Downloader ECS service ID"
  value       = aws_ecs_service.downloader.id
}

output "task_definition_arn" {
  description = "Downloader task definition ARN"
  value       = aws_ecs_task_definition.downloader.arn
}

output "task_definition_family" {
  description = "Downloader task definition family"
  value       = aws_ecs_task_definition.downloader.family
}

output "task_definition_revision" {
  description = "Downloader task definition revision"
  value       = aws_ecs_task_definition.downloader.revision
}

output "log_group_name" {
  description = "CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.downloader.name
}