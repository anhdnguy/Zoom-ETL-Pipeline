locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Developer   = "AnhNguyen"
  }
  repo_root = abspath("${path.root}/../../../")
}

# Networking Module
module "networking" {
  source = "../../modules/network"

  aws_region = var.aws_region

  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr           = var.vpc_cidr
  availability_zones = var.availability_zones

  public_subnet_cidrs  = var.public_subnet_cidrs
  private_subnet_cidrs = var.private_subnet_cidrs

  # Cost saving: No NAT Gateway in dev (Fargate tasks won't have internet)
  # Set to true if you need outbound internet access for API calls
  enable_nat_gateway = true
  single_nat_gateway = true
}

# Secrets Module - Secrets Manager for credentials
module "secrets" {
  source = "../../modules/secrets"

  project_name = var.project_name
  environment  = var.environment
}

# Data Lake Module - S3-based storage
module "datalake" {
  source = "../../modules/datalake"

  project_name = var.project_name
  environment  = var.environment
}

# IAM Module
module "iam" {
  source = "../../modules/iam"

  project_name = var.project_name
  environment  = var.environment

  s3_bucket_arn               = module.datalake.datalake_bucket_arn
  s3_bucket_id                = module.datalake.datalake_bucket_name
  cloudfront_distribution_arn = module.cloudfront.distribution_arn
  sqs_queue_arn               = module.sqs.queue_arn
  ecr_repository_arns         = module.ecr.repository_arns
  zoom_secret_arn             = module.secrets.zoom_credentials_secret_arn
  cloudfront_secret_arn       = module.secrets.cloudfront_credentials_secret_arn
}

# CloudFront Module - Streaming
module "cloudfront" {
  source = "../../modules/cloudfront"

  project_name                = var.project_name
  environment                 = var.environment
  s3_bucket_id                = module.datalake.datalake_bucket_name
  bucket_regional_domain_name = module.datalake.bucket_regional_domain_name
}

# ECRs
module "ecr" {
  source = "../../modules/ecr"

  project_name = var.project_name
  environment  = var.environment
}

# ECS cluster
module "ecs" {
  source             = "../../modules/ecs"
  project_name       = var.project_name
  environment        = var.environment
  log_retention_days = 30
}

# Redis module
module "redis" {
  source       = "../../modules/redis"
  project_name = var.project_name
  environment  = var.environment

  vpc_id                  = module.networking.vpc_id
  private_subnet_ids      = module.networking.private_subnet_ids
  redis_security_group_id = module.networking.redis_security_group_id

  node_type       = var.redis_node_type
  num_cache_nodes = var.redis_num_cache_nodes
  engine_version  = var.redis_engine_version
}

# Airflow Database module
module "database" {
  source       = "../../modules/database"
  project_name = var.project_name
  environment  = var.environment

  vpc_id               = module.networking.vpc_id
  private_subnet_ids   = module.networking.private_subnet_ids
  db_security_group_id = module.networking.db_security_group_id

  instance_class          = var.rds_instance_class
  allocated_storage       = var.rds_allocated_storage
  backup_retention_period = var.rds_backup_retention
}

# SQS module
module "sqs" {
  source       = "../../modules/sqs"
  project_name = var.project_name
  environment  = var.environment
}

# Lambda module
module "lambda" {
  source       = "../../modules/lambda"
  project_name = var.project_name
  environment  = var.environment

  lambda_role_arn          = module.iam.lambda_role_arn
  sqs_queue_url            = module.sqs.queue_url
  private_subnet_ids       = module.networking.private_subnet_ids
  datalake_bucket_name     = module.datalake.datalake_bucket_name
  lambda_security_group_id = module.networking.lambda_security_group_id
  secret_name              = module.secrets.zoom_credentials_secret_name

  lambda_runtime     = var.lambda_runtime
  lambda_handler     = var.lambda_handler
  lambda_memory_size = var.lambda_memory_size
  lambda_timeout     = var.lambda_timeout
  lambda_source_dir  = var.lambda_source_dir
  region             = var.aws_region
}

# Downloader module
module "downloader" {
  source       = "../../modules/downloader"
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  ecs_cluster_id   = module.ecs.cluster_id
  ecs_cluster_name = module.ecs.cluster_name

  vpc_id                       = module.networking.vpc_id
  private_subnet_ids           = module.networking.private_subnet_ids
  downloader_security_group_id = module.networking.downloader_security_group_id

  task_role_arn      = module.iam.downloader_task_role_arn
  execution_role_arn = module.iam.downloader_execution_role_arn

  ecr_repository_url = module.ecr.downloader_repository_url

  sqs_queue_url  = module.sqs.queue_url
  sqs_queue_arn  = module.sqs.queue_arn
  sqs_queue_name = module.sqs.queue_name

  s3_raw_bucket = module.datalake.datalake_bucket_name

  cloudfront_domain = module.cloudfront.cloudfront_distribution_domain_name

  secrets_arn = module.secrets.cloudfront_credentials_secret_arn

  downloader_cpu         = var.downloader_cpu
  downloader_memory      = var.downloader_memory
  download_desired_count = var.downloader_desired_count
  downloader_max_tasks   = var.downloader_max_tasks
}

# Airflow module
module "airflow" {
  source       = "../../modules/airflow"
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  ecs_cluster_id   = module.ecs.cluster_id
  ecs_cluster_name = module.ecs.cluster_name

  vpc_id                    = module.networking.vpc_id
  vpc_cidr                  = var.vpc_cidr
  private_subnet_ids        = module.networking.private_subnet_ids
  airflow_security_group_id = module.networking.airflow_security_group_id

  task_role_arn      = module.iam.airflow_task_role_arn
  execution_role_arn = module.iam.airflow_execution_role_arn

  ecr_repository_url = module.ecr.airflow_repository_url

  database_host     = module.database.endpoint
  database_name     = module.database.database_name
  database_username = module.database.username
  database_password = module.database.password

  redis_host = module.redis.endpoint
  redis_port = module.redis.port

  s3_raw_bucket = module.datalake.datalake_bucket_name

  secrets_arn = module.secrets.zoom_credentials_secret_arn

  airflow_cpu    = var.airflow_cpu
  airflow_memory = var.airflow_memory
  desired_count  = var.airflow_desired_count
  max_capacity   = var.airflow_max_capacity
}