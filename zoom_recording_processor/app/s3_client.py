# app/s3_uploader.py
import boto3
from typing import BinaryIO, Optional
from botocore.exceptions import ClientError
from app.exceptions import S3UploadError, S3BucketNotFoundError
from app.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)

class S3Uploader:
    """Handles uploading recordings to S3"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3', region_name=Config.AWS_REGION)
        self.bucket_name = Config.S3_BUCKET_NAME
    
    
    def check_if_exists(self, s3_key: str) -> bool:
        """
        Check if recording already exists in S3 (for idempotency).
        
        Returns:
            True if object exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                raise S3UploadError(f"Error checking S3 object: {str(e)}")
            
    def abort_incomplete_uploads(self, s3_key: str):
        """
        Abort any incomplete multipart uploads for this key.
        
        This cleans up partial uploads from previous failed attempts.
        Should be called BEFORE starting a new upload.
        
        Args:
            s3_key: S3 key to check for incomplete uploads
        """
        try:
            # List all in-progress multipart uploads for this key
            response = self.s3_client.list_multipart_uploads(
                Bucket=self.bucket_name,
                Prefix=s3_key
            )
            
            uploads = response.get('Uploads', [])
            
            if not uploads:
                logger.debug(f"No incomplete uploads found for {s3_key}")
                return
            
            # Abort each incomplete upload
            for upload in uploads:
                upload_id = upload['UploadId']
                logger.warning(
                    f"Found incomplete upload for {s3_key}, "
                    f"aborting upload_id={upload_id}"
                )
                
                self.s3_client.abort_multipart_upload(
                    Bucket=self.bucket_name,
                    Key=s3_key,
                    UploadId=upload_id
                )
                
                logger.info(f"Aborted incomplete upload: {upload_id}")
        
        except ClientError as e:
            # Don't fail the entire operation if abort fails
            logger.error(f"Error aborting incomplete uploads: {str(e)}")
    
    def upload_stream(
        self,
        file_obj: BinaryIO,
        s3_key: str,
        content_type: str = 'application/octet-stream',
        content_diposition: str = 'inline',
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file to S3 using streaming upload.
        
        For large files (>100MB), this uses multipart upload automatically.
        
        Args:
            file_obj: File-like object to upload (already contains data)
            s3_key: S3 key (path) to upload to
            content_type: MIME type
            metadata: Optional metadata tags
        
        Returns:
            S3 URL of uploaded object
        
        Raises:
            S3UploadError: If upload fails
        """
        try:
            logger.info(f"Uploading to s3://{self.bucket_name}/{s3_key}")
            
            extra_args = {
                'ContentType': content_type,
                'ContentDisposition': content_diposition
            }
            
            if metadata:
                extra_args['Metadata'] = metadata
            
            # Upload with automatic multipart for large files
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )
            
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Upload complete: {s3_url}")
            
            return s3_url
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'NoSuchBucket':
                raise S3BucketNotFoundError(f"Bucket not found: {self.bucket_name}")
            else:
                raise S3UploadError(f"S3 upload failed: {str(e)}")
        
        except Exception as e:
            # If upload fails, try to abort it
            logger.error(f"Upload failed, aborting: {str(e)}")
            self.abort_incomplete_uploads(s3_key)
            raise S3UploadError(f"S3 upload failed: {str(e)}")
        
    def upload_object(
        self,
        data_string: str,
        s3_key: str
    ) -> str:
        """
        Upload recording metadata to S3 Data Lake
        Args:
            data_string: The zoom recording metadata in JSON String format
            s3_key: S3 key (path) to upload to
        
        Returns:
            S3 URL of uploaded object

        Raises:
            S3UploadError: If upload fails
        """
        try:
            logger.info(f"Uploading to s3://{self.bucket_name}/{s3_key}")

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=data_string
            )
            s3_url = f"s3://{self.bucket_name}/{s3_key}"
            logger.info(f"Upload complete: {s3_url}")

            return s3_url
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'NoSuchBucket':
                raise S3BucketNotFoundError(f"Bucket not found: {self.bucket_name}")
            else:
                raise S3UploadError(f"S3 upload failed: {str(e)}")
            
        except Exception as e:
            # If upload fails, try to abort it
            logger.error(f"Upload failed, aborting: {str(e)}")
            self.abort_incomplete_uploads(s3_key)
            raise S3UploadError(f"S3 upload failed: {str(e)}")
        
# Global instance
s3_uploader = S3Uploader()