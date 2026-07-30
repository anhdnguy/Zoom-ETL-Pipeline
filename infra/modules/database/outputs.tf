output "endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.airflow.endpoint
}

output "address" {
  description = "RDS address"
  value       = aws_db_instance.airflow.address
}

output "port" {
  description = "RDS port"
  value       = aws_db_instance.airflow.port
}

output "database_name" {
  description = "Database name"
  value       = aws_db_instance.airflow.db_name
}

output "username" {
  description = "Database username"
  value       = aws_db_instance.airflow.username
  sensitive   = true
}

output "password" {
  description = "Database password"
  value       = random_password.db_password.result
  sensitive   = true
}

output "credentials_secret_arn" {
  description = "ARN of the DB credentials secret in Secrets Manager"
  value       = aws_secretsmanager_secret.db_credentials.arn
  sensitive   = true
}