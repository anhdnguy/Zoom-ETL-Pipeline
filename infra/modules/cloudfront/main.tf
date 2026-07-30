# =============================================================================
# CLOUDFRONT MODULE
# Purpose: CloudFront for fast delivery
# =============================================================================

# CloudFront Origin Access Control (OAC)
# This allows CloudFront to access S3 without making bucket public
resource "aws_cloudfront_origin_access_control" "recordings" {
  name                              = "zoom-recordings-oac"
  description                       = "OAC for Zoom recordings S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always" # CRITICAL: Always sign requests
  signing_protocol                  = "sigv4"  # Use AWS Signature Version 4
}

# Create CloudFront public key (you upload your public key here)
resource "aws_cloudfront_public_key" "zoom_recordings" {
  comment     = "Public key for Zoom recordings signed URLs"
  encoded_key = file("../../cloudfront-public-key.pem")
  name        = "zoom-recordings-public-key"
}

# Create Key Group (collection of public keys)
resource "aws_cloudfront_key_group" "zoom_recordings" {
  comment = "Key group for Zoom recordings"
  items   = [aws_cloudfront_public_key.zoom_recordings.id]
  name    = "zoom-recordings-key-group"
}

# CloudFront Distribution
resource "aws_cloudfront_distribution" "recordings" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.project_name}-${var.environment} distribution"
  default_root_object = ""
  price_class         = var.environment == "prod" ? "PriceClass_200" : "PriceClass_100"
  http_version        = "http2and3"

  origin {
    domain_name              = var.bucket_regional_domain_name
    origin_id                = var.s3_bucket_id
    origin_access_control_id = aws_cloudfront_origin_access_control.recordings.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = var.s3_bucket_id

    forwarded_values {
      query_string = false
      headers      = ["Origin", "Access-Control-Request-Headers", "Access-Control-Request-Method"]

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 86400   # 1 day
    max_ttl                = 2592000 # 30 days
    compress               = true

    trusted_key_groups = [aws_cloudfront_key_group.zoom_recordings.id]
  }

  # Cache behavior for recordings (longer TTL, aggressive caching)
  ordered_cache_behavior {
    path_pattern     = "recordings/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = var.s3_bucket_id

    forwarded_values {
      query_string = false
      headers      = ["Origin"]

      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
    min_ttl                = 0
    default_ttl            = 604800   # 7 days (recordings don't change)
    max_ttl                = 31536000 # 1 year
    compress               = true

    # Enable smooth streaming for video
    smooth_streaming = false
  }

  # Geographic restrictions
  restrictions {
    geo_restriction {
      restriction_type = "none"
      # For future, might want to whitelist specific countries:
      # restriction_type = "whitelist"
      # locations        = ["US", "NP", "VN"]
    }
  }

  # SSL Certificate
  viewer_certificate {
    cloudfront_default_certificate = true
    # minimum_protocol_version       = "TLSv1.2_2021"

    # For custom domain (future enhancement):
    # acm_certificate_arn      = aws_acm_certificate.cert.arn
    # ssl_support_method       = "sni-only"
    # minimum_protocol_version = "TLSv1.2_2021"
  }

  # Custom error responses
  custom_error_response {
    error_code            = 403
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 300
  }

  custom_error_response {
    error_code            = 404
    response_code         = 404
    response_page_path    = "/404.html"
    error_caching_min_ttl = 300
  }

  #  logging_config {
  #    include_cookies = false
  #    bucket          = var.bucket_regional_domain_name
  #    prefix          = "cloudfront-access-logs/"
  #  }

  tags = {
    Name = "${var.project_name}-${var.environment}-recordings-cdn"
  }
}

# CloudWatch Alarms for CloudFront Monitoring
resource "aws_cloudwatch_metric_alarm" "cloudfront_error_rate" {
  alarm_name          = "${var.project_name}-${var.environment}-cloudfront-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5xxErrorRate"
  namespace           = "AWS/CloudFront"
  period              = 300
  statistic           = "Average"
  threshold           = 5
  alarm_description   = "Alert when CloudFront 5xx error rate exceeds 5%"
  treat_missing_data  = "notBreaching"

  dimensions = {
    DistributionId = aws_cloudfront_distribution.recordings.id
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-cloudfront-error-alarm"
  }
}