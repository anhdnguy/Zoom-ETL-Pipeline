# These outputs will be used by other modules
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "alb_security_group_id" {
  description = "Security group ID for ALB"
  value       = aws_security_group.alb.id
}

output "airflow_security_group_id" {
  description = "Security group ID for Fargate tasks"
  value       = aws_security_group.airflow.id
}

output "lambda_security_group_id" {
  description = "Security group ID for Lambda"
  value       = aws_security_group.lambda.id
}

output "downloader_security_group_id" {
  description = "Security group ID for Downloader"
  value       = aws_security_group.downloader.id
}

output "db_security_group_id" {
  description = "Security group ID for RDS"
  value       = aws_security_group.database.id
}

output "redis_security_group_id" {
  description = "Security group ID for Redis"
  value       = aws_security_group.redis.id
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.main[*].id
}

output "internet_gateway_id" {
  description = "Internet Gateway ID"
  value       = aws_internet_gateway.main.id
}