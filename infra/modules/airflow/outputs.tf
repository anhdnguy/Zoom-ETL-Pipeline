output "service_name" {
  description = "Airflow ECS service name"
  value       = aws_ecs_service.airflow.name
}

output "service_id" {
  description = "Airflow ECS service ID"
  value       = aws_ecs_service.airflow.id
}

output "task_definition_arn" {
  description = "Airflow task definition ARN"
  value       = aws_ecs_task_definition.airflow.arn
}

output "task_definition_family" {
  description = "Airflow task definition family"
  value       = aws_ecs_task_definition.airflow.family
}

output "task_definition_revision" {
  description = "Airflow task definition revision"
  value       = aws_ecs_task_definition.airflow.revision
}

output "log_group_name" {
  description = "CloudWatch Log Group name"
  value       = aws_cloudwatch_log_group.airflow.name
}