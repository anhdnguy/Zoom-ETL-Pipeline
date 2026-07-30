import json
import os
import boto3
import logging
from botocore.exceptions import ClientError
from app.exceptions import SQSDeliveryError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

SQS_QUEUE_URL = os.environ["SQS_QUEUE_URL"]

def send_to_sqs(recording_id, recording_metadata):
    message_body = json.dumps(recording_metadata)

    # Check if FIFO queue (ends with .fifo)
    is_fifo = SQS_QUEUE_URL.endswith('.fifo')
    
    params = {
        'QueueUrl': SQS_QUEUE_URL,
        'MessageBody': message_body,
    }
    
    # Only add FIFO-specific parameters if using FIFO queue
    if is_fifo:
        params['MessageGroupId'] = recording_id
        # Optional: Add MessageDeduplicationId for exactly-once processing
        params['MessageDeduplicationId'] = recording_id
    
    logger.info(json.dumps({
        "message": f"Sending recording {recording_id} to SQS",
        'recording_id': recording_id,
        'meeting_uuid': recording_metadata.get('meeting_uuid'),
        'recording_type': recording_metadata.get('recording_type')
    }))

    try:
        logger.info(f"Sending message to SQS", extra={
            'recording_id': recording_id,
            'queue_type': 'FIFO' if is_fifo else 'Standard',
            'message_size': len(message_body)
        })

        sqs = boto3.client("sqs")
        response = sqs.send_message(**params)
        
        logger.info(f"Message sent successfully", extra={
            'message_id': response['MessageId'],
            'recording_id': recording_id
        })
        
        return response
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        logger.error(f"SQS ClientError: {error_code} - {error_message}", extra={
            'recording_id': recording_id,
            'error_code': error_code
        })
        
        raise SQSDeliveryError(f"Failed to send message: {error_message}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error sending to SQS: {e}", exc_info=True, extra={
            'recording_id': recording_id
        })
        raise SQSDeliveryError(f"Unexpected error: {str(e)}") from e