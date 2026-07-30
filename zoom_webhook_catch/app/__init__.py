"""Configuration management module."""

from app.lambda_function import (
    lambda_handler, handle_recording_webhook, _return_fn,
    verify_zoom_signature, handle_verification_challenge,
    select_preferred_recordings
)

from app.secret_client import get_secret
from app.sqs_client import send_to_sqs
from app.exceptions import (
    ZoomWebhookError,
    WebhookValidationError,
    SignatureVerificationError,
    InvalidPayloadError,
    SQSDeliveryError,
    ConfigurationError,
    TimestampValidationError
)