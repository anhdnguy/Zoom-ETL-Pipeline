output "dns_name" {
  description = "Internal ALB DNS name to access Airflow UI"
  value       = aws_lb.airflow.dns_name
}

output "target_group_arn" {
  value = aws_lb_target_group.webserver.arn
}

output "listener_arn" {
  value = aws_lb_listener.http.arn
}