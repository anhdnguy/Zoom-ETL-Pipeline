variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "region" {
  description = "AWS Region"
  type        = string
}

variable "lambda_runtime" {
  description = "Runtime"
  type        = string
  default     = "python3.11"
}

variable "lambda_handler" {
  description = "Handler Fucntion"
  type        = string
  default     = "app.lambda_function.lambda_handler"
}

variable "lambda_memory_size" {
  description = "Memory Size"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Timeout"
  type        = number
  default     = 60
}

variable "lambda_source_dir" {
  description = "Code Directory"
  type        = string
  default     = "../../../zoom_webhook_catch/zoom_webhook.zip"
}

variable "lambda_role_arn" {
  description = "Lambda IAM role ARN"
  type        = string
}

variable "sqs_queue_url" {
  description = "SQS Queue URL"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs for Lambda"
  type        = list(string)
}

variable "lambda_security_group_id" {
  description = "Security group ID for Lambda"
  type        = string
}

variable "datalake_bucket_name" {
  description = "Bucket Name"
  type        = string
}

variable "secret_name" {
  description = "Secret Name"
  type        = string
}