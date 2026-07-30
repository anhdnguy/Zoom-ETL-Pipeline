# =============================================================================
# DATALAKE MODULE
# Purpose: Store user, meeting, participants, recording metadata, recording
# =============================================================================

data "aws_caller_identity" "current" {}

# S3 Bucket for Data Lake
resource "aws_s3_bucket" "datalake" {
  bucket = "${var.project_name}-datalake"

  tags = {
    Name               = "${var.project_name}-${var.environment}-datalake",
    DataClassification = "Internal"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for data protection
resource "aws_s3_bucket_versioning" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Encryption at rest
resource "aws_s3_bucket_server_side_encryption_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
    bucket_key_enabled = true
  }
}

# Lifecycle rules for data management
resource "aws_s3_bucket_lifecycle_configuration" "datalake" {
  bucket = aws_s3_bucket.datalake.id

  # Raw data - keep for 365 days, then archive
  rule {
    id     = "archive-raw-data"
    status = "Enabled"

    filter {
      prefix = "${var.environment}/raw/"
    }

    transition {
      days          = 365
      storage_class = "GLACIER"
    }

    expiration {
      days = 730
    }

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }

  # Recording - keep for a year, then archive
  rule {
    id     = "archive-recording"
    status = "Enabled"

    filter {
      prefix = "${var.environment}/recording_file/"
    }

    # Move to Infrequent Access after 180 days
    transition {
      days          = 180
      storage_class = "STANDARD_IA"
    }

    # Move to Glacier after 365 days
    transition {
      days          = 365
      storage_class = "GLACIER"
    }
  }
}

# Glue Crawler IAM Role
resource "aws_iam_role" "glue_crawler" {
  name = "${var.project_name}-glue-crawler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name = "${var.project_name}-${var.environment}-glue-role"
  }
}

resource "aws_iam_role_policy_attachment" "glue_service_role" {
  role       = aws_iam_role.glue_crawler.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Policy for Glue to access S3 Data Lake
resource "aws_iam_role_policy" "glue_s3_access" {
  name = "${var.project_name}-glue-s3-access"
  role = aws_iam_role.glue_crawler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [aws_s3_bucket.datalake.arn]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = [
          "${aws_s3_bucket.datalake.arn}/*"
        ]
      }
    ]
  })
}


/*
# AWS Glue Database for Data Catalog
resource "aws_glue_catalog_database" "zoom_data" {
  name        = "${var.project_name}_${var.environment}_data"
  description = "Glue catalog for Zoom ETL data lake"

  create_table_default_permission {
    permissions = ["SELECT"]

    principal {
      data_lake_principal_identifier = "IAM_ALLOWED_PRINCIPALS"
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-glue-database"
  }
}

# Glue Crawler for Users
resource "aws_glue_crawler" "users" {
  name          = "${var.project_name}-users-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.zoom_data.name

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/${var.environment}/raw/users/"
  }

  configuration = jsonencode(
    {
      CreatePartitionIndex = true
      Version              = 1.0
    }
  )

  schedule = "cron(0 5 * * ? *)" # Daily at 5 AM UTC

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "LOG"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-user-job"
  }
}

# Glue Crawler for Meetings
resource "aws_glue_crawler" "meetings" {
  name          = "${var.project_name}-meetings-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.zoom_data.name

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/${var.environment}/raw/meetings/"
  }

  configuration = jsonencode(
    {
      CreatePartitionIndex = true
      Version              = 1.0
    }
  )

  schedule = "cron(0 5 * * ? *)" # Daily at 5 AM UTC

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "LOG"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-meeting-job"
  }
}

# Glue Crawler for Participants
resource "aws_glue_crawler" "participants" {
  name          = "${var.project_name}-participants-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.zoom_data.name

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/${var.environment}/raw/participants/"
  }

  configuration = jsonencode(
    {
      CreatePartitionIndex = true
      Version              = 1.0
    }
  )

  schedule = "cron(0 5 * * ? *)" # Daily at 5 AM UTC

  recrawl_policy {
    recrawl_behavior = "CRAWL_NEW_FOLDERS_ONLY"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "LOG"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-participant-job"
  }
}

# Glue Crawler for Recording metadata
resource "aws_glue_crawler" "recordings" {
  name          = "${var.project_name}-recordings-crawler"
  role          = aws_iam_role.glue_crawler.arn
  database_name = aws_glue_catalog_database.zoom_data.name

  s3_target {
    path = "s3://${aws_s3_bucket.datalake.id}/${var.environment}/raw/recordings/"
  }

  configuration = jsonencode(
    {
      CreatePartitionIndex = true
      Version              = 1.0
    }
  )

  schedule = "cron(0 5 * * ? *)" # Daily at 5 AM UTC

  recrawl_policy {
    recrawl_behavior = "CRAWL_EVERYTHING"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "LOG"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-recording-job"
  }
}

# Athena Workgroup for queries
resource "aws_athena_workgroup" "zoom_analytics" {
  name = "${var.project_name}-analytics"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${aws_s3_bucket.datalake.id}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-athena"
  }
}
*/
