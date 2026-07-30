# app/dynamodb_client.py
import boto3
from typing import Any
from datetime import datetime, timezone
from botocore.exceptions import ClientError
from app.exceptions import DBPutError
from app.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)

class DynamoDBClient:
    """Handles Upsert recording metadata to DynamoDB"""

    def __init__(self):
        self.db_client = boto3.resource('dynamodb', region_name=Config.AWS_REGION)
        self.table = self.db_client.Table(Config.DYNAMODB_TABLE_NAME)

    def put_recording(self, recording_info: dict[str, Any]):
        """
        Put item to DynamoDB table.

        Args:
            metadata: dictionary type to put to dynamodb
        
        Returns:
            NA

        Raise:
            Exception for errors
        """
        recording_id = recording_info["recording_id"]
        item = {
            "recording_id": recording_id,
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
            "s3_key_recording_file": recording_info['s3_key_recording'],
            "delete_status": "pending",
            "meeting_uuid": recording_info["meeting_uuid"],
            "retry_count": 0
        }
        try:
            self.table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(recording_id)",
            )
            logger.info(f"Recorded {recording_id} as pending deletion")
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                logger.info(f"{recording_id} already tracked, skipping")
                return
            raise DBPutError(f"Put item failed: {e}")

# Global instance
dynamodb_op = DynamoDBClient()