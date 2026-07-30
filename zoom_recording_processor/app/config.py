# config.py
import os
from typing import Dict

class Config:
    """Application configuration loaded from environment variables"""
    
    # AWS Configuration
    AWS_REGION: str = os.getenv('AWS_REGION', 'us-west-1')
    
    # SQS Configuration
    SQS_QUEUE_URL: str = os.getenv('SQS_QUEUE_URL')  # Required
    SQS_MAX_MESSAGES: int = int(os.getenv('SQS_MAX_MESSAGES', '10'))
    SQS_WAIT_TIME_SECONDS: int = int(os.getenv('SQS_WAIT_TIME_SECONDS', '20'))
    SQS_VISIBILITY_TIMEOUT: int = int(os.getenv('SQS_VISIBILITY_TIMEOUT', '600'))  # 10 min
    
    # S3 Configuration
    S3_BUCKET_NAME: str = os.getenv('S3_BUCKET_NAME')  # Required
    S3_PREFIX: str = os.getenv('ENVIRONMENT', 'zoom-recordings/')  # Optional prefix
    S3_CONTENT_TYPE: Dict = {
        "mp4": "video/mp4",
        "m4a": "audio/mp4",
        "txt": "text/plain; charset=utf-8",
        "cc.vtt": "text/vtt",
        "vtt": "text/vtt",
        "csv": "text/csv; charset=utf-8",
        "json": "application/json; charset=utf-8"
    }

    # CloudFront Configuration
    CLOUDFRONT_DOMAIN: str = os.getenv('CLOUDFRONT_DOMAIN')  # e.g., d123abc456.cloudfront.net
    CLOUDFRONT_KEY_PAIR_ID: str = os.getenv('CLOUDFRONT_KEY_PAIR_ID')
    CLOUDFRONT_PRIVATE_KEY: str = os.getenv('CLOUDFRONT_PRIVATE_KEY')
    CLOUDFRONT_URL_EXPIRATION: int = int(os.getenv('CLOUDFRONT_URL_EXPIRATION', '86400'))  # 24 hours default

    # DynamoDB Configuration
    DYNAMODB_TABLE_NAME: str = os.getenv('DYNAMODB_TABLE_NAME')
    
    # Zoom Configuration
    ZOOM_SECRET_NAME: str = os.getenv('ZOOM_SECRET_NAME', 'zoom-oauth-credentials')
    ZOOM_API_BASE_URL: str = 'https://api.zoom.us/v2'
    
    # Processing Configuration
    CONCURRENT_WORKERS: int = int(os.getenv('CONCURRENT_WORKERS', '5'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY: int = int(os.getenv('RETRY_DELAY', '5'))  # seconds
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    # Streaming Configuration (for large files)
    DOWNLOAD_CHUNK_SIZE: int = int(os.getenv('DOWNLOAD_CHUNK_SIZE', '83886008'))  # 8 MB chunks
    UPLOAD_CHUNK_SIZE: int = int(os.getenv('UPLOAD_CHUNK_SIZE', '83886008'))      # 8 MB chunks
    
    @classmethod
    def validate(cls):
        """Validate required configuration on startup"""
        errors = []
        
        if not cls.SQS_QUEUE_URL:
            errors.append("SQS_QUEUE_URL is required")
        
        if not cls.S3_BUCKET_NAME:
            errors.append("S3_BUCKET_NAME is required")

        if not cls.CLOUDFRONT_DOMAIN:
            errors.append("CLOUDFRONT_DOMAIN is required")
        
        if cls.CONCURRENT_WORKERS < 1 or cls.CONCURRENT_WORKERS > 10:
            errors.append("CONCURRENT_WORKERS must be between 1 and 10")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

# Validate on import
Config.validate()