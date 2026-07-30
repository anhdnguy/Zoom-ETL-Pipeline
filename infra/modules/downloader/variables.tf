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

variable "ecs_cluster_id" {
  description = "ECS Cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS Cluster name"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "downloader_security_group_id" {
  description = "Security group ID for downloader tasks"
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
  description = "ECR repository URL for downloader image"
  type        = string
}

variable "sqs_queue_url" {
  description = "SQS Queue URL"
  type        = string
}

variable "sqs_queue_arn" {
  description = "SQS Queue ARN"
  type        = string
}

variable "sqs_queue_name" {
  description = "SQS Queue Name"
  type        = string
}

variable "s3_raw_bucket" {
  description = "S3 raw bucket name"
  type        = string
}

variable "dynamodb_table" {
  description = "DynamoDB Table Name"
  type        = string
}

variable "cloudfront_domain" {
  description = "CloudFront distribution domain"
  type        = string
}

variable "secrets_arn" {
  description = "Secrets Manager ARN for Cloudfront Keys"
  type        = string
}

variable "downloader_cpu" {
  description = "CPU units for downloader task"
  type        = number
  default     = 2048
}

variable "downloader_memory" {
  description = "Memory (MB) for downloader task"
  type        = number
  default     = 4096
}

variable "download_desired_count" {
  description = "Desired number of downloader tasks"
  type        = number
  default     = 1
}

variable "downloader_max_tasks" {
  description = "Maximum number of concurrent downloader tasks"
  type        = number
  default     = 10
}