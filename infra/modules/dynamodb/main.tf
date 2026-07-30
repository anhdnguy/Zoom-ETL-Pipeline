# =============================================================================
# DYNAMODB MODULE
# Purpose: Storing successfully downloaded recordings for deletion
# =============================================================================

locals {
  prefix = "${var.project_name}-${var.environment}"
}

resource "aws_dynamodb_table" "app" {
  name         = "${local.prefix}-app"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "recording_id"

  attribute {
    name = "recording_id"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name = "${local.prefix}-app"
  }
}