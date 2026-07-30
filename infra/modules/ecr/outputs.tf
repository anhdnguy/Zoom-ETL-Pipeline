output "airflow_repository_url" {
  description = "Airflow ECR repository URL"
  value       = aws_ecr_repository.airflow.repository_url
}

output "airflow_repository_arn" {
  description = "Airflow ECR repository ARN"
  value       = aws_ecr_repository.airflow.arn
}

output "airflow_repository_name" {
  description = "Airflow ECR repository name"
  value       = aws_ecr_repository.airflow.name
}

output "downloader_repository_url" {
  description = "Downloader ECR repository URL"
  value       = aws_ecr_repository.downloader.repository_url
}

output "downloader_repository_arn" {
  description = "Downloader ECR repository ARN"
  value       = aws_ecr_repository.downloader.arn
}

output "downloader_repository_name" {
  description = "Downloader ECR repository name"
  value       = aws_ecr_repository.downloader.name
}

output "repository_arns" {
  description = "Map of all ECR repository ARNs"
  value = {
    airflow    = aws_ecr_repository.airflow.arn
    downloader = aws_ecr_repository.downloader.arn
  }
}