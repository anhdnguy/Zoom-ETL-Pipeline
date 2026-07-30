# =============================================================================
# PROD ENVIRONMENT OUTPUTS
# These will be displayed after terraform apply
# =============================================================================

# ─── Daily Use ─────────────────────────────────

output "alb_dns_name" {
  description = "Airflow UI endpoint (via SSM tunnel or direct if public)"
  value       = module.alb.dns_name
}

output "ecs_cluster_name" {
  description = "ECS cluster name (for aws ecs commands)"
  value       = module.ecs.cluster_name
}

output "s3_bucket_name" {
  description = "Data lake S3 bucket"
  value       = module.datalake.datalake_bucket_name
}

output "ecr_repositories" {
  description = "ECR repository URLs for docker push"
  value = {
    airflow    = module.ecr.airflow_repository_url
    downloader = module.ecr.downloader_repository_url
  }
}

# ─── Service Names (for aws ecs update-service) ──────────────

output "ecs_services" {
  description = "ECS service names for redeployment commands"
  value = {
    webserver  = module.webserver.service_name
    scheduler  = module.scheduler.service_name
    triggerer  = module.triggerer.service_name
    worker     = module.worker.service_name
    downloader = module.downloader.service_name
  }
}

# ─── Log Groups (for aws logs tail) ──────────────────────────

output "log_groups" {
  description = "CloudWatch log groups for debugging"
  value = {
    webserver  = module.webserver.log_group_name
    scheduler  = module.scheduler.log_group_name
    triggerer  = module.triggerer.log_group_name
    worker     = module.worker.log_group_name
    downloader = module.downloader.log_group_name
    lambda     = module.lambda.log_group_name
  }
}

# ─── Endpoints ────────────────────────────────────────────────

output "sqs_queue_url" {
  description = "SQS queue URL for recording events"
  value       = module.sqs.queue_url
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain for recording playback"
  value       = module.cloudfront.cloudfront_distribution_domain_name
}

output "lambda_webhook_url" {
  description = "Zoom webhook endpoint URL (configure in Zoom App Marketplace)"
  value       = module.lambda.function_url
}

# ─── Secrets (sensitive — hidden from plan output) ────────────

output "secrets" {
  description = "Secrets Manager ARNs"
  sensitive   = true # REMOVE FROM DISPLAY — ARNs expose naming patterns
  value = {
    zoom_credentials = module.secrets.zoom_credentials_secret_arn
    cloudfront_keys  = module.secrets.cloudfront_credentials_secret_arn
  }
}

# ─── Network (rarely needed — mark sensitive to reduce noise) ─

output "vpc_id" {
  description = "VPC ID"
  value       = module.networking.vpc_id
  sensitive   = true # REMOVE FROM DISPLAY — only needed for manual debugging
}

output "private_subnet_ids" {
  description = "Private subnet IDs (needed for one-off ECS run-task commands)"
  value       = module.networking.private_subnet_ids
  sensitive   = true # REMOVE FROM DISPLAY — use 'terraform output -json private_subnet_ids' when needed
}

output "airflow_security_group_id" {
  description = "Airflow tasks security group (needed for one-off ECS run-task commands)"
  value       = module.networking.airflow_security_group_id
  sensitive   = true # REMOVE FROM DISPLAY — use 'terraform output -raw airflow_security_group_id' when needed
}

# ─── Convenience Commands ─────────────────────────────────────

output "ssm_tunnel_command" {
  description = "Run this to access Airflow UI via SSM"
  value       = <<-EOT
TASK_ARN=$(aws ecs list-tasks --cluster ${module.ecs.cluster_name} --service-name ${module.webserver.service_name} --query 'taskArns[0]' --output text --profile ${var.profile}) && \
TASK_ID=$(echo "$TASK_ARN" | awk -F/ '{print $NF}') && \
RUNTIME_ID=$(aws ecs describe-tasks --cluster ${module.ecs.cluster_name} --tasks "$TASK_ARN" --query 'tasks[0].containers[0].runtimeId' --output text --profile ${var.profile}) && \
aws ssm start-session \
  --target "ecs:${module.ecs.cluster_name}_$${TASK_ID}_$${RUNTIME_ID}" \
  --document-name AWS-StartPortForwardingSessionToRemoteHost \
  --parameters '{"host":["${module.alb.dns_name}"],"portNumber":["8080"],"localPortNumber":["9090"]}' \
  --profile ${var.profile}
EOT
}

output "redeploy_all_command" {
  description = "Run this to force redeploy all Airflow services"
  value       = "for svc in ${module.webserver.service_name} ${module.scheduler.service_name} ${module.triggerer.service_name} ${module.worker.service_name}; do aws ecs update-service --profile ${var.profile} --cluster ${module.ecs.cluster_name} --service $svc --force-new-deployment; done"
}

output "dag_upload_command" {
  description = "Run this to sync DAGs to S3"
  value       = "aws s3 sync ../airflow/dags/ s3://${module.datalake.datalake_bucket_name}/airflow-dags/ --delete --profile ${var.profile}"
}

# ─── Summary ──────────────────────────────────────────────────

output "summary" {
  description = "Infrastructure quick reference"
  value       = <<-EOT

  ╔═══════════════════════════════════════════════════════════════╗
  ║                  ZOOM ETL — ${upper(var.environment)} ENVIRONMENT                  ║
  ╠═══════════════════════════════════════════════════════════════╣
  ║                                                               ║
  ║  Region:     ${var.aws_region}                                         ║
  ║  Cluster:    ${module.ecs.cluster_name}                  ║
  ║                                                               ║
  ║  AIRFLOW UI                                                   ║
  ║  ───────────                                                  ║
  ║  ALB:        ${module.alb.dns_name}  ║
  ║  Access:     SSM tunnel → http://localhost:8080               ║
  ║                                                               ║
  ║  DATA                                                         ║
  ║  ────                                                         ║
  ║  S3 Bucket:  ${module.datalake.datalake_bucket_name}                       ║
  ║  CloudFront: ${module.cloudfront.cloudfront_distribution_domain_name}              ║
  ║                                                               ║
  ║  WEBHOOK                                                      ║
  ║  ───────                                                      ║
  ║  Zoom URL:   ${module.lambda.function_url}  ║
  ║  SQS Queue:  ${module.sqs.queue_name}       ║
  ║                                                               ║
  ║  DOCKER PUSH                                                  ║
  ║  ───────────                                                  ║
  ║  Airflow:    ${module.ecr.airflow_repository_url}    ║
  ║  Downloader: ${module.ecr.downloader_repository_url} ║
  ║                                                               ║
  ║  QUICK COMMANDS                                               ║
  ║  ──────────────                                               ║
  ║  Tail logs:  aws logs tail <log-group> --follow --since 5m    ║
  ║  Redeploy:   terraform output -raw redeploy_all_command | bash║
  ║  SSM tunnel: terraform output -raw ssm_tunnel_command | bash  ║
  ║  Sync DAGs:  terraform output -raw dag_upload_command | bash  ║
  ║                                                               ║
  ╚═══════════════════════════════════════════════════════════════╝

  EOT
}