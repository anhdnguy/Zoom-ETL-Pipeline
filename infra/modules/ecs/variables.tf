variable "project_name" {
  description = "Project name for resource naming"
  type        = string
}

variable "environment" {
  description = "Environment name (dev or prod)"
  type        = string
}

variable "vpc_id" {
  type = string
}

variable "log_retention_days" {
  description = "Number of retention in days"
  type        = number
  default     = 30
}