# =============================================================================
# DEV ENVIRONMENT OUTPUTS
# These will be displayed after terraform apply
# =============================================================================

# Network Outputs
output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = module.networking.public_subnet_ids
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = module.networking.private_subnet_ids
}

# Storage Outputs
output "s3_bucket_name" {
  description = "Data lake S3 bucket name"
  value       = module.datalake.datalake_bucket_name
}

# Cloudwatch Outputs
output "cloudfront_ID" {
  description = "CloudFront distribution ID"
  value       = module.cloudfront.cloudfront_distribution_id
}

output "cloudfront_distribution_domain" {
  description = "CloudFront distribution domain name"
  value       = module.cloudfront.cloudfront_distribution_domain_name
}

# SQS Outputs
output "sqs_queue_url" {
  description = "SQS Queue URL"
  value       = module.sqs.queue_url
}

# ECR Outputs
output "ecr_repositories" {
  description = "ECR repository URLs"
  value = {
    airflow  = module.ecr.airflow_repository_url
    download = module.ecr.downloader_repository_url
  }
}

# Airflow Outputs
output "airflow_service_id" {
  description = "Airflow ECS service ID"
  value       = module.airflow.service_id
}

output "airflow_task_definition_arn" {
  description = "Airflow task definition ARN"
  value       = module.airflow.task_definition_arn
}

# Downloader Outputs
output "downloader_service_id" {
  description = "Downloader ECS service ID"
  value       = module.downloader.service_id
}

output "downloader_task_definition_arn" {
  description = "Downloader task definition ARN"
  value       = module.downloader.task_definition_arn
}

# SQS
output "sqs_url" {
  description = "SQS Queue URL"
  value       = module.sqs.queue_url
}

# Secrets
output "zoom_credentials_secret_arn" {
  description = "ARN of the Zoom credentials secret"
  value       = module.secrets.zoom_credentials_secret_arn
}

output "zoom_credentials_secret_name" {
  description = "Name of the Zoom credentials secret"
  value       = module.secrets.zoom_credentials_secret_name
}

output "cloudfront_credentials_secret_arn" {
  description = "ARN of the CloudFront credentials secret"
  value       = module.secrets.cloudfront_credentials_secret_arn
}

output "cloudfront_credentials_secret_name" {
  description = "Name of the CloudFront credentials secret"
  value       = module.secrets.cloudfront_credentials_secret_name
}

# Monitoring Outputs
output "cloudwatch_log_groups" {
  description = "CloudWatch Log Groups"
  value = {
    airflow             = module.airflow.log_group_name
    downloader          = module.downloader.log_group_name
    ecs                 = module.ecs.log_group
    recording_processor = module.lambda.log_group_name
  }
}

#Quick Summary
output "output_summary" {
  description = "Quick reference"
  value       = <<-EOT
    ===================================================================
    INFRASTRUCTURE ACCESS SUMMARY
    ===================================================================

    Environment: ${var.environment}
    Region: ${var.aws_region}

     --- S3 BUCKETS ---
    Storage: ${module.datalake.datalake_bucket_name}

     --- CLOUDFRONT KEY ---
    ID: ${module.cloudfront.key_pair_id}

     --- SQS URL ---
    URL: ${module.sqs.queue_url}
    ===================================================================
  EOT
}