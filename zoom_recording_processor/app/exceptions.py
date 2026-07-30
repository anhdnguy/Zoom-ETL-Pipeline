class ZoomRecordingProcessorError(Exception):
    """Base exception for all application errors"""
    pass

# SQS Exceptions
class SQSError(ZoomRecordingProcessorError):
    """Base SQS error"""
    pass

class SQSMessageParseError(SQSError):
    """Failed to parse SQS message payload"""
    pass

# Zoom API Exceptions
class ZoomAPIError(ZoomRecordingProcessorError):
    """Base Zoom API error"""
    pass

class ZoomAuthenticationError(ZoomAPIError):
    """Zoom OAuth token is invalid or expired"""
    pass

class ZoomRecordingNotFoundError(ZoomAPIError):
    """Recording not found in Zoom"""
    pass

class ZoomRateLimitError(ZoomAPIError):
    """Hit Zoom API rate limit (429)"""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after  # Seconds to wait
        super().__init__(f"Rate limited. Retry after {retry_after} seconds")

class ZoomDownloadError(ZoomAPIError):
    """Failed to download recording from Zoom"""
    pass

# S3 Exceptions
class S3Error(ZoomRecordingProcessorError):
    """Base S3 error"""
    pass

class S3UploadError(S3Error):
    """Failed to upload recording to S3"""
    pass

class S3BucketNotFoundError(S3Error):
    """S3 bucket does not exist"""
    pass

# DynamoDB Exceptions
class DBError(ZoomRecordingProcessorError):
    """Base DynamoDB error"""
    pass
class DBPutError(DBError):
    """Failed to put item to table"""
    pass

# Secrets Manager Exceptions
class SecretsManagerError(ZoomRecordingProcessorError):
    """Failed to retrieve secret from AWS Secrets Manager"""
    pass

# Retry Exceptions (should retry)
class RetryableError(ZoomRecordingProcessorError):
    """Error that should trigger a retry"""
    pass

# Fatal Exceptions (should NOT retry)
class FatalError(ZoomRecordingProcessorError):
    """Error that should not be retried"""
    pass