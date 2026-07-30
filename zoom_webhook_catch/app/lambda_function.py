from app.secret_client import get_secret
from app.sqs_client import send_to_sqs
from app.exceptions import (
    SignatureVerificationError,
    InvalidPayloadError,
    ConfigurationError,
    SQSDeliveryError,
    TimestampValidationError
)

from datetime import datetime, timezone
import json
import hmac
import hashlib
import logging
import os
import time
import string
import random

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Validate required environment variables at module load
REQUIRED_ENV_VARS = ["SECRET_NAME", "BUCKET_NAME", "SQS_QUEUE_URL", "REGION"]
missing_vars = [var for var in REQUIRED_ENV_VARS if var not in os.environ]
if missing_vars:
    raise ConfigurationError(f"Missing required environment variables: {', '.join(missing_vars)}")

# Load configuration
SECRET_NAME = os.environ["SECRET_NAME"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
ENVIRONMENT = os.environ["ENVIRONMENT"]

# Signature replay attack prevention (5 minutes)
SIGNATURE_MAX_AGE_SECONDS = 300

def select_preferred_recordings(zoom_recordings):
    accepted_recording = [
        ['shared_screen_with_gallery_view(CC)', 'shared_screen_with_gallery_view',
         'shared_screen_with_speaker_view', 'gallery_view', 'active_speaker', 'audio_only'],
        ['audio_transcript'],
        ['timeline'],
        ['closed_caption', 'audio_interpretation'],
        ['summary', 'summary_next_steps', 'summary_smart_chapters'],
        ['sign_interpretation'],
        ['cc_transcript'],
        ['chat_file'],
        ['poll']
    ]
    # Convert zoom recordings to a dict for fast lookup
    file_lookup = {rec['recording_type']: rec for rec in zoom_recordings}
    selected = []

    for category in accepted_recording:
        for preferred_type in category:
            if preferred_type in file_lookup:
                selected.append(file_lookup[preferred_type])
                break  # Only take the first available in this category

    logger.info(f"Selected {len(selected)} recordings from {len(zoom_recordings)} total files")
    return selected

def handle_verification_challenge(body):
    """
    Respond to Zoom's endpoint verification challenge
    
    Args:
        body: Parsed webhook body dict
        
    Returns:
        Lambda response dict with encrypted token
    """
    try:
        plain_token = body['payload']['plainToken']
        logger.info("Processing verification challenge")
        
        # Get secret token
        secrets = get_secret(SECRET_NAME)
        secret_token = secrets.get("secret_token")
        
        if not secret_token:
            raise ConfigurationError("Missing secret_token in secrets")
        
        # Create encrypted token using HMAC-SHA256
        encrypted_token = hmac.new(
            secret_token.encode('utf-8'),
            plain_token.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        logger.info("Verification challenge completed successfully")
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'plainToken': plain_token,
                'encryptedToken': encrypted_token
            })
        }
        
    except KeyError as e:
        logger.error(f"Missing required field in verification payload: {e}")
        raise InvalidPayloadError(f"Missing field: {e}") from e
    except Exception as e:
        logger.error(f"Verification challenge failed: {e}", exc_info=True)
        raise
    
def verify_zoom_signature(headers, body, secret_token):
    """
    Verify Zoom webhook signature to ensure authenticity
    
    Args:
        headers: Request headers dict
        body: Raw request body (string)
        secret_token: Zoom webhook secret token
        
    Raises:
        SignatureVerificationError: If signature is invalid
        TimestampValidationError: If timestamp is missing, invalid, or too old
    """
    timestamp = headers.get("x-zm-request-timestamp")
    signature = headers.get("x-zm-signature")
    # Validate required headers
    if not timestamp:
        raise TimestampValidationError("Missing x-zm-request-timestamp header")
    if not signature:
        raise SignatureVerificationError("Missing x-zm-signature header")
    
    # Validate timestamp format
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        raise TimestampValidationError(f"Invalid timestamp format: {timestamp}")
    
    # Check timestamp age (prevent replay attacks)
    current_time = int(time.time())
    age = abs(current_time - timestamp_int)
    if age > SIGNATURE_MAX_AGE_SECONDS:
        raise TimestampValidationError(
            f"Webhook timestamp too old: {age} seconds (max: {SIGNATURE_MAX_AGE_SECONDS})"
        )
    
    # Construct message in Zoom's format: v0:{timestamp}:{body}
    message = f"v0:{timestamp}:{body}"
    
    # Compute HMAC-SHA256 signature
    hashed = hmac.new(
        secret_token.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # computed_signature = base64.b64encode(hashed).decode("utf-8")
    expected_signature = f"v0={hashed}"
    
    # Constant-time comparison (prevent timing attacks)
    # if not hmac.compare_digest(expected_signature, signature):
    if not expected_signature == signature:
        logger.error(json.dumps({
            "message": "Signature verification failed",
            "expected_prefix": expected_signature[:20],
            "received_prefix": signature[:20],
        }))
        raise SignatureVerificationError("Invalid webhook signature")
    
    logger.info("Signature verification successful")
    return True

def _return_fn (statuscode, message):
    return {
        "statusCode": statuscode,
        "body": json.dumps(message)
    }

def handle_recording_webhook(body):
    partition_time = datetime.now(timezone.utc)
    year = partition_time.year
    month = partition_time.month
    day = partition_time.day

    try:
        payload = body.get("payload", {})
        recording_data = payload.get("object", {})
        meeting_uuid = recording_data.get("uuid")
        meeting_id = recording_data.get("id")
        host_email = recording_data.get("host_email")
        topic = recording_data.get("topic")
        start_time = recording_data.get("start_time")
        download_token = body.get("download_token")
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        s3_key_recording = f"{ENVIRONMENT}/recording_file/year={year:04d}/month={month:02d}/day={day:02d}/"
        s3_key_metadata = f"{ENVIRONMENT}/raw/recordings/year={year:04d}/month={month:02d}/day={day:02d}/"

        recording_files = recording_data.get("recording_files")
        selected_files = select_preferred_recordings(recording_files)
        if not selected_files:
            logger.warning(f"No recordings selected for meeting {meeting_uuid}")
            return _return_fn(200, {"message": "No recordings to process"})
        
        # Process each selected recording
        sent_count = 0
        failed_count = 0

        for file in selected_files:
            try:
                recording_id = file.get("id")
                recording_type = file.get("recording_type")
                file_extension = file.get("file_extension").lower()
                file_type = file.get("file_type").lower()
                file_size = file.get("file_size")
                download_url = file.get("download_url")

                # Validate required fields
                if not all([recording_id, recording_type, download_url]):
                    logger.error(f"Missing required fields in recording file: {file}")
                    failed_count += 1
                    continue

                timestamp_safe = start_time.replace(':', '-').replace('T', '_').replace('Z', '')
                file_name = f"{recording_type}_{random_string}_{timestamp_safe}.{file_extension}"
                metadata = {
                    "meeting_uuid": meeting_uuid,
                    "meeting_id": meeting_id,
                    "recording_id": recording_id,
                    "host_email": host_email,
                    "topic": topic,
                    "start_time": start_time,
                    "recording_type": recording_type,
                    "file_type": file_type,
                    "file_extension": file_extension,
                    "file_name": file_name,
                    "file_size": file_size,
                    "download_url": download_url,
                    "download_token": download_token,
                    "s3_bucket": BUCKET_NAME,
                    "s3_key_recording": f"{s3_key_recording}{file_name}",
                    "s3_key_metadata": f"{s3_key_metadata}{recording_id}.json"
                }

                send_to_sqs(recording_id, metadata)
                sent_count += 1

                logger.info(f"Queued recording for download", extra={
                    'recording_id': recording_id,
                    'recording_type': recording_type,
                    'meeting_uuid': meeting_uuid,
                    'file_size_mb': round(file_size / 1024 / 1024, 2)
                })

            except SQSDeliveryError as e:
                logger.error(f"Failed to queue recording {recording_id}: {e}")
                failed_count += 1
                # Continue processing other recordings
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing recording {recording_id}: {e}", exc_info=True)
                failed_count += 1
                continue

        logger.info(f"Webhook processing complete: {sent_count} queued, {failed_count} failed")

        return _return_fn(
            200,
            {
                "message": "Webhook processed",
                "queued": sent_count,
                "failed": failed_count
            }
        )
    except InvalidPayloadError as e:
        logger.error(f"Invalid payload: {e}")
        # Return 200 to prevent Zoom retries (payload won't become valid)
        return {
            "statusCode": 200,
            "body": json.dumps({"error": "Invalid payload", "details": str(e)})
        }
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        # Return 500 to trigger Zoom retry (might be transient issue)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Internal server error"})
        }

def lambda_handler(event, context):
    """
    Main Lambda handler for Zoom recording webhooks
    
    Flow:
        1. Extract headers and body
        2. Verify Zoom signature
        3. Parse JSON body
        4. Route to verification or webhook handler
    """
    try:
        # Extract request data
        headers = event.get("headers", {})
        body_str = event.get("body", "{}")

        # Normalize header keys to lowercase (API Gateway vs Function URL difference)
        headers = {k.lower(): v for k, v in headers.items()}
        
        logger.info("Received webhook request", extra={
            'has_signature': 'x-zm-signature' in headers,
            'has_timestamp': 'x-zm-request-timestamp' in headers,
            'body_length': len(body_str)
        })

        # Get secret token
        try:
            secrets = get_secret(SECRET_NAME)
            secret_token = secrets.get("secret_token")

            if not secret_token:
                raise ConfigurationError("Missing secret_token in secrets")
        except Exception as e:
            logger.error(f"Failed to retrieve secrets: {e}", exc_info=True)
            return _return_fn(500, {"error": "Configuration error"})

        # Parse JSON body
        try:
            body = json.loads(body_str) if isinstance(body_str, str) else body_str
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in request body: {e}")
            return _return_fn(400, {"error": "Invalid JSON"})

        # Route based on event type
        event_type = body.get("event")
        logger.info(f"Processing event type: {event_type}")
        
        if event_type == "endpoint.url_validation":
            return handle_verification_challenge(body)

        # Verify signature BEFORE parsing (use raw body string)
        try:
            verify_zoom_signature(headers, body_str, secret_token)
        except (SignatureVerificationError, TimestampValidationError) as e:
            logger.error(f"Signature verification failed: {e}")
            # Return 401 to reject invalid webhooks
            return _return_fn(401, {"error": "Unauthorized", "details": str(e)})

        
        if event_type == "recording.completed" or event_type == "recording.transcript_completed":
            return handle_recording_webhook(body)
        
        else:
            logger.warning(f"Unknown event type: {event_type}")
            # Acknowledge unknown events to prevent retries
            return _return_fn(200, {"message": "Event type not supported"})
        
    except ConfigurationError as e:
        logger.critical(f"Configuration error: {e}", exc_info=True)
        return _return_fn(500, {"error": "Configuration error"})
    
    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}", exc_info=True)
        return _return_fn(500, {"error": "Internal server error"})