# =============================================================================
# AIRFLOW MODULE
# Purpose: Extract metadata from Zoom
# =============================================================================

locals {
  full_name = "${var.project_name}-${var.environment}-${var.service_name}"
}

# CloudWatch Log Group for Airflow
resource "aws_cloudwatch_log_group" "airflow" {
  name              = "/ecs/${var.project_name}-${var.environment}-${var.service_name}"
  retention_in_days = var.environment == "prod" ? 30 : 7

  tags = {
    Name = local.full_name
  }
}

# ECS Task Definition for Airflow
resource "aws_ecs_task_definition" "airflow" {
  family                   = local.full_name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.airflow_cpu
  memory                   = var.airflow_memory
  task_role_arn            = var.task_role_arn
  execution_role_arn       = var.execution_role_arn

  container_definitions = jsonencode([
    {
      name       = "${var.service_name}"
      image      = "${var.ecr_repository_url}:3.8"
      entryPoint = ["/opt/airflow/entrypoint.sh"]
      command    = "${var.command}"
      essential  = true

      environment = [
        # Core
        {
          name  = "AIRFLOW__CORE__EXECUTOR"
          value = var.environment == "prod" ? "CeleryExecutor" : "LocalExecutor"
        },
        {
          name  = "AIRFLOW__CORE__LOAD_EXAMPLES"
          value = "False"
        },
        {
          name  = "AIRFLOW__CORE__DAGS_FOLDER"
          value = "/opt/airflow/dags"
        },
        {
          name  = "AIRFLOW__LOGGING__REMOTE_LOGGING"
          value = "True"
        },
        {
          name  = "AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER"
          value = "s3://${var.s3_raw_bucket}/airflow-logs"
        },
        {
          name  = "AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID"
          value = "aws_default"
        },
        {
          name  = "AIRFLOW__CORE__HOSTNAME_CALLABLE"
          value = var.service_name == "worker" ? "hostname_helper.get_hostname" : "airflow.utils.net.getfqdn"
        },

        # Database connection (PostgreSQL)
        {
          name  = "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN"
          value = "postgresql+psycopg2://${var.database_username}:${var.database_password}@${var.database_host}:${var.database_port}/${var.database_name}"
        },

        # Redis connection (for Celery in prod)
        {
          name  = "REDIS_HOST"
          value = "${var.redis_host}"
        },
        {
          name  = "REDIS_PORT"
          value = "${tostring(var.redis_port)}"
        },
        {
          name  = "AIRFLOW__CELERY__BROKER_URL"
          value = var.environment == "prod" ? "redis://${var.redis_host}:${var.redis_port}/0" : ""
        },
        {
          name  = "AIRFLOW__CELERY__RESULT_BACKEND"
          value = var.environment == "prod" ? "db+postgresql://${var.database_username}:${var.database_password}@${var.database_host}:${var.database_port}/${var.database_name}" : ""
        },
        # Webserver
        {
          name  = "AIRFLOW__API__BASE_URL"
          value = "http://${var.dns_name}:8080"
        },
        {
          name  = "AIRFLOW__CORE__EXECUTION_API_SERVER_URL"
          value = "http://webserver.airflow.local:8080/execution/"
        },
        {
          name  = "AIRFLOW__API__EXPOSE_CONFIG"
          value = "False"
        },
        {
          name  = "AIRFLOW__API__RBAC"
          value = "True"
        },
        {
          name  = "AIRFLOW__API__WARN_DEPLOYMENT_EXPOSURE"
          value = "False"
        },

        # AWS Configuration
        {
          name  = "AWS_REGION"
          value = var.aws_region
        },
        {
          name  = "S3_BUCKET"
          value = var.s3_raw_bucket
        },
        {
          name  = "AIRFLOW_S3_DAGS_URI"
          value = "s3://${var.s3_raw_bucket}/airflow-dags/"
        },
        {
          name  = "ENVIRONMENT"
          value = var.environment
        },
        {
          name  = "PROJECT_NAME"
          value = var.project_name
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
          name  = "MAX_RETRIES"
          value = "3"
        },
        {
          name  = "BATCH_SIZE"
          value = "100"
        },
        {
          name  = "DEFAULT_PAGE_SIZE"
          value = "300"
        },

        # Scheduler
        {
          name  = "AIRFLOW__SCHEDULER__ENABLE_HEALTH_CHECK"
          value = "True"
        },

        # API (needed for triggerer and programmatic access)
        {
          name  = "AIRFLOW__API__AUTH_BACKENDS"
          value = "airflow.api.auth.backend.session"
        }
      ]

      portMappings = [{
        containerPort = var.container_port
        protocol      = "tcp"
      }]

      # Secrets from Secrets Manager
      secrets = [
        {
          name      = "Client_ID"
          valueFrom = "${var.secrets_arn}:client_id::"
        },
        {
          name      = "Client_Secret"
          valueFrom = "${var.secrets_arn}:client_secret::"
        },
        {
          name      = "account_ID"
          valueFrom = "${var.secrets_arn}:account_id::"
        },
        {
          name      = "AIRFLOW__CORE__FERNET_KEY"
          valueFrom = "${var.secrets_arn}:AIRFLOW__CORE__FERNET_KEY::"
        },
        {
          name      = "AIRFLOW__API__SECRET_KEY"
          valueFrom = "${var.secrets_arn}:AIRFLOW__API__SECRET_KEY::"
        },
        {
          name      = "AIRFLOW__API_AUTH__JWT_SECRET"
          valueFrom = "${var.secrets_arn}:AIRFLOW__API_AUTH__JWT_SECRET::"
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.airflow.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = var.service_name
        }
      }

      # Container health check (optional)
      healthCheck = var.health_check_command != null ? {
        command     = var.health_check_command
        interval    = var.health_check_interval
        retries     = var.health_check_retries
        startPeriod = var.health_check_start_period
        timeout     = 10
      } : null

      # Resource limits
      ulimits = [
        {
          name      = "nofile"
          softLimit = 65536
          hardLimit = 65536
        }
      ]
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "ARM64" # Image supports ARM64
  }

  tags = {
    Name = local.full_name
  }
}

# ─── Service Discovery ────────────────────────────────────────
# Registers each service so it's reachable at:
#   <service_name>.airflow.local
# ─────────────────────────────────────────────────────────────

resource "aws_service_discovery_service" "service" {
  name = var.service_name

  dns_config {
    namespace_id   = var.service_discovery_namespace_id
    routing_policy = "MULTIVALUE"

    dns_records {
      type = "A"
      ttl  = 10
    }
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# ECS Service for Airflow (long-running)
resource "aws_ecs_service" "airflow" {
  name            = local.full_name
  cluster         = var.ecs_cluster_id
  task_definition = aws_ecs_task_definition.airflow.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  # Deployment circuit breaker — if new tasks keep failing,
  # ECS automatically rolls back instead of looping forever.
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.private_subnet_ids
    security_groups  = [var.airflow_security_group_id]
    assign_public_ip = false
  }

  # Enable ECS Exec for debugging
  enable_execute_command = true

  # Service Discovery registration
  service_registries {
    registry_arn = aws_service_discovery_service.service.arn
  }

  # ALB attachment — only for webserver
  dynamic "load_balancer" {
    for_each = var.target_group_arn != null ? [1] : []
    content {
      target_group_arn = var.target_group_arn
      container_name   = var.service_name
      container_port   = var.container_port
    }
  }

  tags = {
    Name = local.full_name
  }

  # Ensure task definition is updated before modifying service
  lifecycle {
    ignore_changes = [task_definition]
  }
}
