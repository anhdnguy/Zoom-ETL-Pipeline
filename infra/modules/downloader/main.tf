# =============================================================================
# DOWNLOADER MODULE
# Purpose: Download Recordings to S3
# =============================================================================

# CloudWatch Log Group for Downloader
resource "aws_cloudwatch_log_group" "downloader" {
  name              = "/ecs/${var.project_name}-${var.environment}-downloader"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Name = "${var.project_name}-${var.environment}-downloader-logs"
  }
}

# ECS Task Definition for Downloader
resource "aws_ecs_task_definition" "downloader" {
  family                   = "${var.project_name}-${var.environment}-downloader"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.downloader_cpu
  memory                   = var.downloader_memory
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([
    {
      name      = "downloader"
      image     = "${var.ecr_repository_url}:latest"
      essential = true

      environment = [
        {
          name  = "SQS_QUEUE_URL"
          value = var.sqs_queue_url
        },
        {
          name  = "SQS_MAX_MESSAGES"
          value = "10"
        },
        {
          name  = "SQS_WAIT_TIME_SECONDS"
          value = "20"
        },
        {
          name  = "SQS_VISIBILITY_TIMEOUT"
          value = "600"
        },
        {
          name  = "S3_BUCKET_NAME"
          value = var.s3_raw_bucket
        },
        {
          name  = "S3_PREFIX"
          value = "${var.environment}/recording_file/"
        },
        {
          name = "S3_CONTENT_TYPE"
          value = jsonencode({
            mp4  = "video/mp4",
            m4a  = "audio/mp4",
            txt  = "text/plain; charset=utf-8",
            vtt  = "text/vtt",
            csv  = "text/csv; charset=utf-8",
            json = "application/json; charset=utf-8"
          })
        },
        {
          name  = "CLOUDFRONT_DOMAIN"
          value = var.cloudfront_domain
        },
        {
          name  = "CLOUDFRONT_URL_EXPIRATION"
          value = "15552000" # 180 days
        },
        {
          name  = "AWS_DEFAULT_REGION"
          value = var.aws_region
        },
        {
          name  = "DYNAMODB_TABLE_NAME"
          value = var.dynamodb_table
        },
        {
          name  = "LOG_LEVEL"
          value = var.environment == "prod" ? "INFO" : "DEBUG"
        },
        {
          name  = "CONCURRENT_WORKERS"
          value = "5"
        },
        {
          name  = "MAX_RETRIES"
          value = "3"
        },
        {
          name  = "DOWNLOAD_CHUNK_SIZE"
          value = "83886008"
        },
        {
          name  = "UPLOAD_CHUNK_SIZE"
          value = "83886008"
        }
      ]

      secrets = [
        {
          name      = "CLOUDFRONT_KEY_PAIR_ID"
          valueFrom = "${var.secrets_arn}:key_pair_id::"
        },
        {
          name      = "CLOUDFRONT_PRIVATE_KEY"
          valueFrom = "${var.secrets_arn}:private_key::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.downloader.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = {
    Name = "${var.project_name}-${var.environment}-downloader-task"
  }
}

# ECS Service for Downloader (long-running)
resource "aws_ecs_service" "downloader" {
  name            = "${var.project_name}-${var.environment}-downloader"
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.downloader.arn
  desired_count   = var.download_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.downloader_security_group_id]
    assign_public_ip = false
  }

  # Enable ECS Exec for debugging
  enable_execute_command = true

  tags = {
    Name = "${var.project_name}-${var.environment}-downloader-service"
  }
}

resource "aws_appautoscaling_target" "downloader" {
  max_capacity       = var.downloader_max_tasks
  min_capacity       = var.download_desired_count
  resource_id        = "service/${var.ecs_cluster_name}/${aws_ecs_service.downloader.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

# Auto Scaling Policy - SQS based
resource "aws_appautoscaling_policy" "sqs_backlog" {
  name               = "${var.project_name}-${var.environment}-downloader-sqs-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.downloader.resource_id
  scalable_dimension = aws_appautoscaling_target.downloader.scalable_dimension
  service_namespace  = aws_appautoscaling_target.downloader.service_namespace

  target_tracking_scaling_policy_configuration {
    target_value       = 50
    scale_in_cooldown  = 120
    scale_out_cooldown = 30

    customized_metric_specification {
      metric_name = "ApproximateNumberOfMessagesVisible"
      namespace   = "AWS/SQS"
      statistic   = "Sum"

      dimensions {
        name  = "QueueName"
        value = var.sqs_queue_name
      }
    }
  }
}



# CloudWatch Alarms for Downloader Monitoring

# Alarm: No running tasks but queue has messages
resource "aws_cloudwatch_metric_alarm" "no_running_tasks" {
  alarm_name          = "${var.project_name}-${var.environment}-downloader-no-tasks"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  threshold           = 1
  alarm_description   = "Alert when no downloader tasks are running but queue has messages"

  metric_query {
    id          = "m1"
    return_data = true
    metric {
      metric_name = "RunningTaskCount"
      namespace   = "ECS/ContainerInsights"
      period      = 60
      stat        = "Minimum"
      dimensions = {
        ClusterName = var.ecs_cluster_name
        ServiceName = "${aws_ecs_service.downloader.name}"
      }
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-downloader-no-tasks-alarm"
  }
}

# Alarm: High task failure rate
resource "aws_cloudwatch_log_metric_filter" "task_failures" {
  name           = "${var.project_name}-${var.environment}-downloader-failures"
  log_group_name = aws_cloudwatch_log_group.downloader.name
  pattern        = "[time, request_id, level = ERROR*, ...]"

  metric_transformation {
    name      = "DownloaderTaskFailures"
    namespace = "${var.project_name}/${var.environment}"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "task_failures" {
  alarm_name          = "${var.project_name}-${var.environment}-downloader-failures"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "DownloaderTaskFailures"
  namespace           = "${var.project_name}/${var.environment}"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "Alert when downloader has more than 10 failures in 10 minutes"
  treat_missing_data  = "notBreaching"

  tags = {
    Name = "${var.project_name}-${var.environment}-downloader-failures-alarm"
  }
}