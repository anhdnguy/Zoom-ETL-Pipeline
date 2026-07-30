import boto3
from botocore.exceptions import ClientError
from typing import Dict

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

from src.config import AppConfig
from src.storage.s3_exceptions import (
    S3BucketNotFoundError,
    S3GetHeadObjectError
)

class S3Reader:
    """
    Verify Zoom recordings in S3
    """

    def __init__(self, config: AppConfig):
        self.config = config
        self.bucket = config.s3_bucket
        self.base_prefix = config.environment
        self.s3 = boto3.client("s3", region_name=config.aws_region)

    def get_head_object(self, key: str) -> Dict:
        try:
            logger.info(f"Getting HEAD object: s3://{self.bucket}/{key}")
            head = self.s3.head_object(Bucket=self.bucket, Key=key)
            return head
        except ClientError as e:
            error_code = e.response['Error']['Code']

            if error_code == 'NoSuchBucket':
                raise S3BucketNotFoundError(f"Bucket not found: {self.bucket_name}")
            else:
                raise S3GetHeadObjectError(f"Get HEAD object failed: {key}")