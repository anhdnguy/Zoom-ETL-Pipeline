variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-1"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "zoom-etl"
}

variable "cost_center" {
  description = "Cost center for billing allocation"
  type        = string
  default     = "Technology"
}

variable "profile" {
  description = "Profile of AWS"
  type        = string
  default     = "default"
}

# Networking Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.30.0.0/16"
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["us-west-1a", "us-west-1b"]
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.30.1.0/24", "10.30.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private application subnets"
  type        = list(string)
  default     = ["10.30.11.0/24", "10.30.12.0/24"]
}

variable "enable_nat_gateway" {
  description = "NAT Gateway enable"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Single NAT Gateway fpr cost optimization"
  type        = bool
  default     = true
}

# Downloader Configuration
variable "downloader_cpu" {
  description = "CPU units for downloader task"
  type        = number
  default     = 2048
}

variable "downloader_memory" {
  description = "Memory (MB) for downloader task"
  type        = number
  default     = 4096
}

variable "downloader_desired_count" {
  description = "Desired number of downloader tasks"
  type        = number
  default     = 1
}

variable "downloader_max_tasks" {
  description = "Maximum number of concurrent downloader tasks"
  type        = number
  default     = 5
}

# Airflow Configuration
variable "airflow_cpu" {
  description = "CPU units for Airflow scheduler (1024 = 1 vCPU)"
  type        = number
  default     = 1024
}

variable "airflow_memory" {
  description = "Memory for Airflow scheduler in MB"
  type        = number
  default     = 2048
}

variable "airflow_desired_count" {
  description = "Desired number of Airflow tasks"
  type        = number
  default     = 1
}

variable "airflow_max_capacity" {
  description = "Maximum number of Airflow tasks for auto-scaling"
  type        = number
  default     = 3
}

# RDS (PostgreSQL for Airflow)
variable "rds_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.large"
}

variable "rds_allocated_storage" {
  description = "Initial allocated storage for RDS in GB"
  type        = number
  default     = 100
  validation {
    condition     = var.rds_allocated_storage >= 20 && var.rds_allocated_storage <= 65536
    error_message = "RDS allocated storage must be between 20 and 65536 GB."
  }
}

variable "rds_backup_retention" {
  description = "Number of days to retain RDS backups"
  type        = number
  default     = 30
  validation {
    condition     = var.rds_backup_retention >= 0 && var.rds_backup_retention <= 35
    error_message = "Backup retention must be between 0 and 35 days."
  }
}

# Redis (Celery broker)
variable "redis_node_type" {
  description = "Redis Node Type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_num_cache_nodes" {
  description = "Redis Number of Cache Nodes"
  type        = number
  default     = 1
}

variable "redis_engine_version" {
  description = "Redis Engine Version"
  type        = string
  default     = "7.0"
}

# Lambda
variable "lambda_runtime" {
  description = "Runtime"
  type        = string
  default     = "python3.11"
}

variable "lambda_handler" {
  description = "Handler Function"
  type        = string
  default     = "app.lambda_function.lambda_handler"
}

variable "lambda_memory_size" {
  description = "Memory Size"
  type        = number
  default     = 256
}

variable "lambda_timeout" {
  description = "Timeout"
  type        = number
  default     = 60
}

variable "lambda_source_dir" {
  description = "Code Directory"
  type        = string
  default     = "../../../zoom_webhook_catch/zoom_webhook.zip"
}

# Cloudwatch
variable "log_retention_in_days" {
  description = "CloudWatch Logs retention period in days"
  type        = number
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_in_days)
    error_message = "Log retention must be a valid CloudWatch retention period."
  }
}