# These outputs will be used by other modules
output "zoom_credentials_secret_arn" {
  description = "ARN of the Zoom credentials secret"
  value       = aws_secretsmanager_secret.zoom_credentials.arn
}

output "zoom_credentials_secret_name" {
  description = "Name of the Zoom credentials secret"
  value       = aws_secretsmanager_secret.zoom_credentials.name
}

output "cloudfront_credentials_secret_arn" {
  description = "ARN of the CloudFront credentials secret"
  value       = aws_secretsmanager_secret.cloudfront.arn
}

output "cloudfront_credentials_secret_name" {
  description = "Name of the CloudFront credentials secret"
  value       = aws_secretsmanager_secret.cloudfront.name
}