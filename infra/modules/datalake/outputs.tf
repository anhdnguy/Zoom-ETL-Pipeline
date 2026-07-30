output "datalake_bucket_name" {
  description = "Name of the data lake S3 bucket"
  value       = aws_s3_bucket.datalake.id
}

output "datalake_bucket_arn" {
  description = "ARN of the data lake S3 bucket"
  value       = aws_s3_bucket.datalake.arn
}

output "bucket_regional_domain_name" {
  description = "Regional Domain"
  value       = aws_s3_bucket.datalake.bucket_regional_domain_name
}

/*
output "glue_database_name" {
  description = "Name of the Glue catalog database"
  value       = aws_glue_catalog_database.zoom_data.name
}

output "athena_workgroup_name" {
  description = "Name of the Athena workgroup"
  value       = aws_athena_workgroup.zoom_analytics.name
}
*/

output "glue_crawler_role_arn" {
  description = "ARN of the Glue crawler IAM role"
  value       = aws_iam_role.glue_crawler.arn
}