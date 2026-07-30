import os
import logging

logger = logging.getLogger(__name__)

class AppConfig:
    """
    Application configuration loaded from environment variables.

    S3_BUCKET: S3 bucket name for data storage

    AWS_REGION: AWS region (default: us-west-1)
    ENVIRONMENT: Environment name (default: dev)
    MAX_RETRIES: Retry attempts for failed operations (default: 3)
    BATCH_SIZE: Records to process per batch (default: 100)
    DEFAULT_PAGE_SIZE: Records per page during pagination (default: 300)
    LOG_LEVEL: Logging level (default: INFO)
    """

    # AWS Settings
    s3_bucket: str = os.getenv("S3_BUCKET")
    aws_region: str = os.getenv("AWS_REGION", "us-west-1")

    # Redis
    redis_host: str = os.getenv("REDIS_HOST")
    redis_port: str = os.getenv("REDIS_PORT")

    # Zoom API Settings
    zoom_api_url: str = "https://api.zoom.us/v2"
    zoom_oauth_token_url: str = "https://zoom.us/oauth/token"
    zoom_api_timeout: int = int(os.getenv("ZOOM_API_TIMEOUT", "30"))
    zoom_client_id: str = os.getenv("Client_ID")
    zoom_client_secret: str = os.getenv("Client_Secret")
    zoom_account_id: str = os.getenv("account_ID")

    # DynamoDB Settings
    dynamodb_table_name: str = os.getenv("DYNAMODB_TABLE_NAME")

    # Application Settings
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    batch_size: int = int(os.getenv("BATCH_SIZE", "100"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    default_page_size: int = int(os.getenv("DEFAULT_PAGE_SIZE", "300"))

    # Environment
    environment: str = os.getenv("ENVIRONMENT", "dev")
    
    @classmethod
    def validate(cls):
        """
        Validate configuration values.
        
        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate S3 Bucket
        if not cls.s3_bucket:
            raise ValueError("S3_BUCKET environment variable is required")
        
        # Validate environment
        valid_environments = ["dev", "staging", "prod"]
        if cls.environment not in valid_environments:
            raise ValueError(
                f"Invalid environment: {cls.environment}. "
                f"Must be one of {valid_environments}"
            )
        
        # Validate numeric ranges
        if cls.max_retries < 1:
            raise ValueError("max_retries must be >= 1")
        
        if cls.batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        
        if cls.zoom_api_timeout < 1:
            raise ValueError("zoom_api_timeout must be >= 1")
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if cls.log_level.upper() not in valid_log_levels:
            raise ValueError(
                f"Invalid log_level: {cls.log_level}. "
                f"Must be one of {valid_log_levels}"
            )
        
        logger.info(
            f"Configuration loaded: environment={cls.environment}, "
            f"s3_bucket={cls.s3_bucket}, region={cls.aws_region}"
        )

# Singleton instance - loaded once when first imported
AppConfig.validate()