output "airflow_task_role_arn" {
  description = "Airflow ECS task role ARN"
  value       = aws_iam_role.airflow_task.arn
}

output "airflow_task_role_name" {
  description = "Airflow ECS task role name"
  value       = aws_iam_role.airflow_task.name
}

output "airflow_execution_role_arn" {
  description = "Airflow ECS execution role ARN"
  value       = aws_iam_role.airflow_execution.arn
}

output "airflow_execution_role_name" {
  description = "Airflow ECS execution role name"
  value       = aws_iam_role.airflow_execution.name
}

output "downloader_task_role_arn" {
  description = "Downloader ECS task role ARN"
  value       = aws_iam_role.downloader_task.arn
}

output "downloader_task_role_name" {
  description = "Downloader ECS task role name"
  value       = aws_iam_role.downloader_task.name
}

output "downloader_execution_role_arn" {
  description = "Downloader ECS execution role ARN"
  value       = aws_iam_role.downloader_execution.arn
}

output "downloader_execution_role_name" {
  description = "Downloader ECS execution role name"
  value       = aws_iam_role.downloader_execution.name
}

output "lambda_role_arn" {
  description = "Lambda function role ARN"
  value       = aws_iam_role.lambda.arn
}

output "lambda_role_name" {
  description = "Lambda function role name"
  value       = aws_iam_role.lambda.name
}

output "aws_s3_bucket_policy_id" {
  description = "Lambda function role name"
  value       = aws_s3_bucket_policy.recording_cloudfront.id
}