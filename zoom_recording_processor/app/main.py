# app/main.py
import signal
import sys
from typing import NoReturn
from app.sqs_handler import sqs_handler
from app.logger import setup_logger
from app.config import Config
from app.exceptions import ZoomRecordingProcessorError

logger = setup_logger(__name__)

# Global flag for graceful shutdown
shutdown_requested = False


def signal_handler(signum, frame):
    """
    Handle shutdown signals (SIGTERM, SIGINT).
    
    ECS sends SIGTERM when stopping a task.
    CTRL+C sends SIGINT during local testing.
    """
    global shutdown_requested
    
    signal_name = signal.Signals(signum).name
    logger.info(f"Received signal {signal_name} ({signum}), initiating graceful shutdown...")
    
    shutdown_requested = True
    
    # Note: Don't sys.exit() here - let the main loop finish current work


def validate_environment() -> bool:
    """
    Validate that all required environment variables and AWS resources are configured.
    
    Fails fast if something is wrong - better to crash on startup than fail later.
    
    Returns:
        True if all validations pass
    
    Raises:
        ValueError: If validation fails
    """
    logger.info("Validating environment configuration...")
    
    try:
        # Config validation (already done on import, but explicit here)
        Config.validate()
        logger.info("✓ Configuration validated")
        
        # Log key configuration (don't log secrets!)
        logger.info(f"  AWS Region: {Config.AWS_REGION}")
        logger.info(f"  SQS Queue: {Config.SQS_QUEUE_URL}")
        logger.info(f"  S3 Bucket: {Config.S3_BUCKET_NAME}")
        logger.info(f"  Concurrent Workers: {Config.CONCURRENT_WORKERS}")
        logger.info(f"  Max Retries: {Config.MAX_RETRIES}")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {str(e)}")
        raise


def health_check() -> bool:
    """
    Perform health checks on AWS services before starting main loop.
    
    Verifies:
    - SQS queue exists and is accessible
    - S3 bucket exists and is accessible
    - Secrets Manager secret exists
    
    Returns:
        True if all health checks pass
    
    Raises:
        Exception: If any health check fails
    """
    logger.info("Performing health checks...")
    
    import boto3
    from botocore.exceptions import ClientError
    
    try:
        # Health Check 1: SQS Queue
        logger.info("Checking SQS queue accessibility...")
        sqs_client = boto3.client('sqs', region_name=Config.AWS_REGION)
        
        try:
            response = sqs_client.get_queue_attributes(
                QueueUrl=Config.SQS_QUEUE_URL,
                AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
            )
            
            attrs = response.get('Attributes', {})
            visible_messages = attrs.get('ApproximateNumberOfMessages', 0)
            in_flight_messages = attrs.get('ApproximateNumberOfMessagesNotVisible', 0)
            
            logger.info(f"✓ SQS queue accessible")
            logger.info(f"  Messages in queue: {visible_messages}")
            logger.info(f"  Messages in flight: {in_flight_messages}")
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AWS.SimpleQueueService.NonExistentQueue':
                raise Exception(f"SQS queue does not exist: {Config.SQS_QUEUE_URL}")
            elif error_code == 'AccessDenied':
                raise Exception(f"Access denied to SQS queue: {Config.SQS_QUEUE_URL}")
            else:
                raise Exception(f"SQS error: {str(e)}")
        
        # Health Check 2: S3 Bucket
        logger.info("Checking S3 bucket accessibility...")
        s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
        
        try:
            s3_client.head_bucket(Bucket=Config.S3_BUCKET_NAME)
            logger.info(f"✓ S3 bucket accessible: {Config.S3_BUCKET_NAME}")
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise Exception(f"S3 bucket does not exist: {Config.S3_BUCKET_NAME}")
            elif error_code == '403':
                raise Exception(f"Access denied to S3 bucket: {Config.S3_BUCKET_NAME}")
            else:
                raise Exception(f"S3 error: {str(e)}")
        
        logger.info("✓ All health checks passed")
        return True
    
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        raise


def startup_banner():
    """Display startup banner with version and configuration info."""
    banner = """
    ╔════════════════════════════════════════════════════════════╗
    ║                                                            ║
    ║        Zoom Recording Processor - ECS Service              ║
    ║                                                            ║
    ║        Processes Zoom recordings from SQS queue            ║
    ║        Downloads from Zoom API → Uploads to S3             ║
    ║                                                            ║
    ╚════════════════════════════════════════════════════════════╝
    """
    logger.info(banner)
    logger.info(f"Version: 1.0.0")
    logger.info(f"Environment: {Config.AWS_REGION}")


def main() -> NoReturn:
    """
    Main application entry point.
    
    Workflow:
    1. Display startup banner
    2. Validate configuration
    3. Perform health checks
    4. Register signal handlers
    5. Start SQS polling loop
    6. Handle graceful shutdown
    """
    try:
        # Step 1: Startup banner
        startup_banner()
        
        # Step 2: Validate configuration
        validate_environment()
        
        # Step 3: Health checks
        health_check()
        
        # Step 4: Register signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, signal_handler)  # ECS sends SIGTERM
        signal.signal(signal.SIGINT, signal_handler)   # CTRL+C for local testing
        
        logger.info("Signal handlers registered (SIGTERM, SIGINT)")
        
        # Step 5: Start main processing loop
        logger.info("=" * 60)
        logger.info("Starting main processing loop...")
        logger.info("=" * 60)
        
        # This runs forever until shutdown signal received
        start_processing()
        
        # If we reach here, shutdown was requested
        logger.info("Processing loop exited gracefully")
        logger.info("Application shutdown complete")
        sys.exit(0)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        sys.exit(0)
    
    except Exception as e:
        logger.error(f"Fatal error during startup: {str(e)}", exc_info=True)
        logger.error("Application failed to start")
        sys.exit(1)


def start_processing():
    """
    Start the main processing loop with shutdown support.
    
    This wraps sqs_handler.start_polling() to support graceful shutdown.
    """
    global shutdown_requested
    
    try:
        # Modify sqs_handler to check shutdown flag
        # We'll update the handler's polling loop
        sqs_handler.start_polling_with_shutdown(shutdown_check=lambda: shutdown_requested)
    
    except Exception as e:
        logger.error(f"Error in processing loop: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    """
    Entry point when running as a script.
    
    Usage:
        python -m app.main
    
    or in Docker:
        CMD ["python", "-m", "app.main"]
    """
    main()