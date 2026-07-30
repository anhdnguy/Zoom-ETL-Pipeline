terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  backend "s3" {
    # Replace with your own state bucket and lock table,
    # or override at init: terraform init -backend-config="bucket=..."
    bucket         = "your-terraform-state-bucket"
    key            = "zoom-etl/dev/terraform.tfstate"
    region         = "us-west-1"
    encrypt        = true
    dynamodb_table = "your-terraform-locks-table"
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.profile

  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.project_name
      ManagedBy   = "Terraform"
      CostCenter  = var.cost_center
    }
  }
}
