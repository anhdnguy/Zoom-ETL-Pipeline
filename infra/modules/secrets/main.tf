# =============================================================================
# SECRET MODULE
# Purpose: Create secret credential
# =============================================================================

# Secrets Manager for Zoom API Credentials
resource "aws_secretsmanager_secret" "zoom_credentials" {
  name                    = "${var.project_name}/${var.environment}/zoom/credentials"
  description             = "Zoom API credentials"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-${var.environment}-zoom-secrets"
  }
}

# Placeholder - will need to manually set these values after creation
resource "aws_secretsmanager_secret_version" "zoom_credentials_placeholder" {
  secret_id = aws_secretsmanager_secret.zoom_credentials.id
  secret_string = jsonencode({
    client_id     = "PLACEHOLDER"
    client_secret = "PLACEHOLDER"
    account_id    = "PLACEHOLDER"
    secret_token  = "PLACEHOLDER"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Secrets Manager for CloudFront
resource "aws_secretsmanager_secret" "cloudfront" {
  name                    = "${var.project_name}/${var.environment}/cloudfront"
  description             = "Cloudfront Private Key"
  recovery_window_in_days = 7

  tags = {
    Name = "${var.project_name}-${var.environment}-cloudfront-secrets"
  }
}

resource "aws_secretsmanager_secret_version" "cloudfront_placeholder" {
  secret_id = aws_secretsmanager_secret.cloudfront.id
  secret_string = jsonencode({
    private_key = file("../../cloudfront-private-key.pem")
    key_pair_id = "PLACEHOLDER"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}