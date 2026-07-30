output "cluster_id" {
  value = aws_ecs_cluster.main.id
}

output "cluster_arn" {
  value = aws_ecs_cluster.main.arn
}

output "cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "service_discovery_namespace_id" {
  value = aws_service_discovery_private_dns_namespace.airflow.id
}

output "log_group" {
  value = aws_cloudwatch_log_group.ecs_exec.name
}