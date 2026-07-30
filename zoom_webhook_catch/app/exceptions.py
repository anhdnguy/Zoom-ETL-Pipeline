# exceptions.py

class ZoomWebhookError(Exception):
    """Base exception for all webhook processing errors"""
    pass

class WebhookValidationError(ZoomWebhookError):
    """Raised when webhook validation fails"""
    pass

class SignatureVerificationError(WebhookValidationError):
    """Raised when Zoom signature verification fails"""
    pass

class InvalidPayloadError(ZoomWebhookError):
    """Raised when webhook payload is malformed or missing required fields"""
    pass

class SQSDeliveryError(ZoomWebhookError):
    """Raised when message cannot be sent to SQS"""
    pass

class ConfigurationError(ZoomWebhookError):
    """Raised when required configuration is missing"""
    pass

class TimestampValidationError(WebhookValidationError):
    """Raised when webhook timestamp is invalid or too old (replay attack)"""
    pass
