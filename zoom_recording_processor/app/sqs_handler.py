# app/sqs_handler.py
import boto3
import json
import io
import time
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError
from app.exceptions import (
    SQSMessageParseError,
    ZoomAuthenticationError,
    ZoomRecordingNotFoundError,
    ZoomRateLimitError,
    ZoomDownloadError,
    S3UploadError,
    DBPutError,
    RetryableError,
    FatalError
)
from app.zoom_client import zoom_client
from app.s3_client import s3_uploader
from app.cloudfront_client import cloudfront_signer
from app.dynamodb_client import dynamodb_op
from app.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)


class SQSHandler:
    """Handles SQS message polling and processing"""
    
    def __init__(self):
        self.sqs_client = boto3.client('sqs', region_name=Config.AWS_REGION)
        self.queue_url = Config.SQS_QUEUE_URL
        self.max_messages = Config.SQS_MAX_MESSAGES
        self.wait_time = Config.SQS_WAIT_TIME_SECONDS
        self.visibility_timeout = Config.SQS_VISIBILITY_TIMEOUT
        
        # Statistics tracking
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'messages_failed': 0,
            'messages_deleted': 0
        }
    
    def _receive_messages(self) -> List[Dict]:
        """
        Receive messages from SQS using long polling.
        
        Returns:
            List of SQS messages (empty if queue is empty)
        """
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=self.max_messages,
                WaitTimeSeconds=self.wait_time,
                VisibilityTimeout=self.visibility_timeout,
                AttributeNames=['ApproximateReceiveCount'],  # For retry tracking
                MessageAttributeNames=['All']
            )
            
            return response.get('Messages', [])
        
        except ClientError as e:
            logger.error(f"Error receiving messages from SQS: {str(e)}")
            return []
    
    def _process_messages_concurrently(self, messages: List[Dict]):
        """
        Process multiple messages concurrently using ThreadPoolExecutor.
        
        Each message is processed in a separate thread.
        Successful messages are deleted; failed messages remain in queue.
        """
        with ThreadPoolExecutor(max_workers=Config.CONCURRENT_WORKERS) as executor:
            # Submit all messages for processing
            future_to_message = {
                executor.submit(self._process_single_message, msg): msg
                for msg in messages
            }
            
            # Wait for all to complete and handle results
            for future in as_completed(future_to_message):
                message = future_to_message[future]
                message_id = message.get('MessageId', 'unknown')
                
                try:
                    # Get result (will raise exception if processing failed)
                    success = future.result()
                    
                    if success:
                        # Delete message from queue
                        self._delete_message(message)
                        self.stats['messages_deleted'] += 1
                    else:
                        # Processing failed but handled - message stays in queue
                        self.stats['messages_failed'] += 1
                
                except Exception as e:
                    # Unexpected error in processing
                    logger.error(
                        f"Unexpected error processing message {message_id}: {str(e)}",
                        exc_info=True
                    )
                    self.stats['messages_failed'] += 1
    
    def _process_single_message(self, message: Dict) -> bool:
        """
        Process a single SQS message: download recording and upload to S3.
        
        Returns:
            True if processing succeeded (message should be deleted)
            False if processing failed but is retryable (message stays in queue)
        
        Raises:
            Exception for unexpected errors
        """
        message_id = message.get('MessageId', 'unknown')
        receive_count = int(message.get('Attributes', {}).get('ApproximateReceiveCount', 1))
        
        logger.info(f"Processing message {message_id} (attempt #{receive_count})")
        
        try:
            # Step 1: Parse message payload
            recording_info = self._parse_message(message)
            
            meeting_id = recording_info['meeting_id']
            recording_id = recording_info['recording_id']
            file_extension = recording_info['file_extension']
            download_url = recording_info['download_url']
            download_token = recording_info['download_token']
            s3_key_recording_file = recording_info['s3_key_recording']
            
            logger.info(
                f"Processing recording: meeting={meeting_id}, "
                f"recording={recording_id}"
            )
            
            # Step 2: Check if already exists (idempotency)
            if s3_uploader.check_if_exists(s3_key_recording_file):
                logger.info(f"Recording already exists in S3: {s3_key_recording_file}")
                # Already processed - safe to delete message
                return True
            
            # Step 3: Download from Zoom and upload to S3 using streaming
            bytes_processed = self._download_and_upload(
                download_url=download_url,
                download_token=download_token,
                s3_key=s3_key_recording_file,
                metadata={
                    'meeting_id': meeting_id,
                    'recording_id': recording_id,
                    'file_extension': file_extension
                }
            )
            
            logger.info(
                f"Successfully processed recording {recording_id}: "
                f"{bytes_processed / (1024*1024):.1f} MB uploaded to {s3_key_recording_file}"
            )
            
            self.stats['messages_processed'] += 1
        
        except SQSMessageParseError as e:
            # Invalid message format - no point retrying
            logger.error(f"Failed to parse message {message_id}: {str(e)}")
            return True  # Delete invalid message (send to DLQ)
        
        except ZoomRecordingNotFoundError as e:
            # Recording doesn't exist - no point retrying
            logger.error(f"Recording not found: {str(e)}")
            return True  # Delete message (recording was deleted from Zoom)
        
        except ZoomAuthenticationError as e:
            # OAuth token issue - could be temporary
            logger.error(f"Zoom authentication failed: {str(e)}")
            # Don't delete - might work after token refresh
            return False
        
        except ZoomRateLimitError as e:
            # Rate limited - will work later
            logger.warning(f"Rate limited: {str(e)}")
            # Don't delete - retry after rate limit expires
            return False
        
        except (ZoomDownloadError, S3UploadError) as e:
            # Network/temporary errors - retry
            logger.error(f"Download/upload failed: {str(e)}")
            
            # Check if we've retried too many times
            if receive_count >= Config.MAX_RETRIES:
                logger.error(
                    f"Message {message_id} exceeded max retries ({Config.MAX_RETRIES}), "
                    f"will be sent to DLQ"
                )
                return True  # Give up, send to DLQ
            
            # Still have retries left
            return False
        
        except Exception as e:
            # Unexpected error - log and don't delete (will retry)
            logger.error(
                f"Unexpected error processing message {message_id}: {str(e)}",
                exc_info=True
            )
            return False
        
        try:
            # Step 4: Generate Signed URL
            signed_url = cloudfront_signer.generate_cloud_presigned_url(
                s3_key_recording_file,
                Config.CLOUDFRONT_URL_EXPIRATION
            )
        except Exception as e:
            logger.error(f"Failed to generate CloudFront URL: {str(e)}")
            return False
        
        try:
            # Step 5: Upload metadata to S3 Data Lake
            recording_info['view_url'] = signed_url
            s3_key_metadata_file = recording_info['s3_key_metadata']
            metadata_str = json.dumps(recording_info)

            s3_uploader.upload_object(
                metadata_str,
                s3_key_metadata_file
            )
        
        except S3UploadError as e:
            # Network/temporary errors - retry
            logger.error(f"Upload metadata failed: {str(e)}")
            
            # Check if we've retried too many times
            if receive_count >= Config.MAX_RETRIES:
                logger.error(
                    f"Message {message_id} exceeded max retries ({Config.MAX_RETRIES}), "
                    f"will be sent to DLQ"
                )
                return True  # Give up, send to DLQ
            
            # Still have retries left
            return False

        except Exception as e:
            logger.error(f"Failed to Upload metadata to S3: {str(e)}")
            return False
        
        try:
            # Step 6: Write record to DynamoDB
            dynamodb_op.put_recording(recording_info)
            return True

        except DBPutError as e:
            # Network/temporary errors - retry
            logger.error(f"Put metadata to DynamoDB failed: {str(e)}")
            
            # Check if we've retried too many times
            if receive_count >= Config.MAX_RETRIES:
                logger.error(
                    f"Message {message_id} exceeded max retries ({Config.MAX_RETRIES}), "
                    f"will be sent to DLQ"
                )
                return True  # Give up, send to DLQ
            
            # Still have retries left
            return False
    
    def _parse_message(self, message: Dict) -> Dict:
        """
        Parse SQS message body and extract recording information.
        
        Expected message format:
        {
            "meeting_id": "123456789",
            "recording_id": "abc-def-ghi",
            "download_url": "https://zoom.us/rec/download/...",
            "file_type": "MP4",
            "topic": "Team Meeting"
        }
        
        Returns:
            Dict with recording information
        
        Raises:
            SQSMessageParseError: If message is invalid
        """
        try:
            body = message.get('Body')
            if not body:
                raise SQSMessageParseError("Message body is empty")
            
            # Parse JSON
            data = json.loads(body)
            
            # Validate required fields
            required_fields = ['meeting_id', 'recording_id', 'download_url']
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                raise SQSMessageParseError(
                    f"Message missing required fields: {missing_fields}"
                )
            
            return data
        
        except json.JSONDecodeError as e:
            raise SQSMessageParseError(f"Invalid JSON in message body: {str(e)}")
        
        except Exception as e:
            raise SQSMessageParseError(f"Failed to parse message: {str(e)}")
        
    def _guess_disposition(self, content_type: str) -> str:
        if content_type.startswith(("text/", "video/", "audio/", "application/json")):
            return "inline"
        return "attachment"
    
    def _download_and_upload(
        self,
        download_url: str,
        download_token: str,
        s3_key: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """
        Download recording from Zoom and upload to S3 using streaming.
        
        This is the core processing logic. Uses in-memory buffer to avoid
        writing large files to disk.
        
        Args:
            download_url: Zoom download URL
            s3_key: S3 destination key
            metadata: Optional metadata for S3 object
        
        Returns:
            Total bytes processed
        
        Raises:
            ZoomDownloadError: If download fails
            S3UploadError: If upload fails
        """
        # Use BytesIO as in-memory buffer for streaming
        # For very large files (>1GB), you might want to use a temporary file
        buffer = io.BytesIO()

        if metadata:
            # S3 metadata must be strings - convert all values
            string_metadata = {
                key: str(value) if value is not None else ''
                for key, value in metadata.items()
            }
        else:
            string_metadata = {}
        
        content_type = Config.S3_CONTENT_TYPE.get(metadata["file_extension"], "application/octet-stream")
        disposition = self._guess_disposition(content_type)
        try:
            # Download from Zoom (streams into buffer)
            logger.info(f"Downloading recording from Zoom...")
            bytes_downloaded = zoom_client.download_recording(download_url, download_token, buffer)
            
            # Rewind buffer to beginning for upload
            buffer.seek(0)
            
            # Upload to S3 (reads from buffer)
            logger.info(f"Uploading to S3: {s3_key}")
            s3_uploader.upload_stream(
                file_obj=buffer,
                s3_key=s3_key,
                content_type=content_type,
                content_diposition=disposition,
                metadata=string_metadata
            )
            
            return bytes_downloaded
        
        finally:
            # Clean up buffer
            buffer.close()
    
    def _delete_message(self, message: Dict):
        """
        Delete message from SQS queue after successful processing.
        
        Args:
            message: SQS message dict
        """
        receipt_handle = message.get('ReceiptHandle')
        message_id = message.get('MessageId', 'unknown')
        
        try:
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=receipt_handle
            )
            logger.info(f"Deleted message {message_id} from queue")
        
        except ClientError as e:
            logger.error(f"Failed to delete message {message_id}: {str(e)}")
            # Don't raise - message will become visible again and be reprocessed
    
    def _log_stats(self):
        """Log processing statistics"""
        logger.info(
            f"Stats: received={self.stats['messages_received']}, "
            f"processed={self.stats['messages_processed']}, "
            f"failed={self.stats['messages_failed']}, "
            f"deleted={self.stats['messages_deleted']}"
        )

    def _log_final_stats(self):
        """Log final statistics on shutdown"""
        logger.info("=" * 60)
        logger.info("FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Total messages received: {self.stats['messages_received']}")
        logger.info(f"Successfully processed: {self.stats['messages_processed']}")
        logger.info(f"Failed: {self.stats['messages_failed']}")
        logger.info(f"Deleted from queue: {self.stats['messages_deleted']}")
        logger.info("=" * 60)
    
    def start_polling_with_shutdown(self, shutdown_check=None):
        """
        Start the infinite polling loop with support for graceful shutdown.
        
        Args:
            shutdown_check: Callable that returns True when shutdown is requested
        """
        logger.info("Starting SQS polling loop...")
        logger.info(f"Queue URL: {self.queue_url}")
        logger.info(f"Concurrent workers: {Config.CONCURRENT_WORKERS}")
        
        while True:
            # Check if shutdown requested
            if shutdown_check and shutdown_check():
                logger.info("Shutdown signal received, stopping polling...")
                logger.info("Waiting for in-flight messages to complete...")
                # Current batch will complete, then exit
                break
            
            try:
                # Poll for messages
                messages = self._receive_messages()
                
                if not messages:
                    # Queue is empty - long polling will wait up to 20s
                    continue
                
                logger.info(f"Received {len(messages)} message(s)")
                self.stats['messages_received'] += len(messages)
                
                # Process messages concurrently
                self._process_messages_concurrently(messages)
                
                # Log stats periodically
                self._log_stats()
            
            except Exception as e:
                # Catch-all for unexpected errors
                logger.error(f"Unexpected error in polling loop: {str(e)}", exc_info=True)
                
                # Check if shutdown requested before continuing
                if shutdown_check and shutdown_check():
                    logger.info("Shutdown during error handling, exiting...")
                    break
                
                # Brief pause before retrying after error
                time.sleep(5)
                continue
        
        logger.info("Polling loop stopped gracefully")
        self._log_final_stats()


# Global instance
sqs_handler = SQSHandler()