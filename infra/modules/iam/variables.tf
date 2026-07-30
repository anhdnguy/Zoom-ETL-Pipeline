variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "s3_bucket_arn" {
  description = "ARN of the raw S3 bucket"
  type        = string
}

variable "s3_bucket_id" {
  description = "ID of the raw S3 bucket"
  type        = string
}

variable "cloudfront_distribution_arn" {
  description = "Cloudfront distribution ARN"
  type        = string
}

variable "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  type        = string
}

variable "ecr_repository_arns" {
  description = "Map of ECR repository ARNs"
  type        = map(string)
}

variable "zoom_secret_arn" {
  description = "ARN of the Zoom Secrets Manager secret"
  type        = string
}

variable "cloudfront_secret_arn" {
  description = "ARN of the Cloudfront Secrets Manager secret"
  type        = string
}

variable "dynamodb_table_arn" {
  description = "DynamoDB table arn"
  type        = string
}