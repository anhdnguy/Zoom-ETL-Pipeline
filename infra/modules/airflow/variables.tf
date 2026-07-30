variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-1"
}

variable "service_name" {
  description = "Airflow component: webserver, scheduler, triggerer, worker"
  type        = string

  validation {
    condition     = contains(["webserver", "scheduler", "triggerer", "worker"], var.service_name)
    error_message = "service_name must be webserver, scheduler, triggerer, or worker."
  }
}

variable "ecs_cluster_id" {
  description = "ECS Cluster ID"
  type        = string
}

variable "service_discovery_namespace_id" {
  type = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "airflow_security_group_id" {
  description = "Security group ID for Airflow tasks"
  type        = string
}

variable "task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "execution_role_arn" {
  description = "ECS execution role ARN"
  type        = string
}

variable "ecr_repository_url" {
  description = "ECR repository URL for Airflow image"
  type        = string
}

variable "command" {
  description = "Airflow command override (e.g., ['airflow', 'webserver'])"
  type        = list(string)
}

variable "database_host" {
  description = "RDS PostgreSQL endpoint"
  type        = string
}

variable "database_name" {
  description = "Database name"
  type        = string
}

variable "database_username" {
  description = "Database username"
  type        = string
  sensitive   = true
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "database_port" {
  description = "Database port"
  type        = number
  sensitive   = true
}

variable "redis_host" {
  description = "Redis endpoint"
  type        = string
}

variable "redis_port" {
  description = "Redis port"
  type        = number
  default     = 6379
}

variable "s3_raw_bucket" {
  description = "S3 raw bucket name"
  type        = string
}

variable "dynamodb_table" {
  description = "DynamoDB Table Name"
  type        = string
}

variable "secrets_arn" {
  description = "Secrets Manager ARN for Zoom credentials"
  type        = string
}

variable "airflow_cpu" {
  description = "CPU units for Airflow task"
  type        = number
  default     = 1024
}

variable "airflow_memory" {
  description = "Memory (MB) for Airflow task"
  type        = number
  default     = 2048
}

variable "desired_count" {
  description = "Desired number of Airflow tasks"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of Airflow tasks for auto-scaling"
  type        = number
  default     = 3
}

variable "target_group_arn" {
  description = "ALB target group ARN. Set only for the webserver."
  type        = string
  default     = null
}

variable "dns_name" {
  type = string
}

variable "container_port" {
  description = "Port the container listens on"
  type        = number
  default     = 8080
}

# ─── Health check ─────────────────────────────────────────────

variable "health_check_command" {
  description = "Container health check command"
  type        = list(string)
  default     = null
}

variable "health_check_interval" {
  type    = number
  default = 30
}

variable "health_check_retries" {
  type    = number
  default = 3
}

variable "health_check_start_period" {
  description = "Grace period before health checks start (seconds). Airflow services are SLOW to start."
  type        = number
  default     = 120
}