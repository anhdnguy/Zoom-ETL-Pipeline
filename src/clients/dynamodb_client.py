import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from datetime import datetime
from typing import List, Dict
from src.config import AppConfig
from src.clients.dynamodb_exceptions import DeleteStatusTypeError, UpdateTableError, ScanTableError

class DynamoDBClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.db_client = boto3.resource('dynamodb', region_name=config.aws_region)
        self.table = self.db_client.Table(config.dynamodb_table_name)

    def scan_records(self, cutoff: datetime) -> List[Dict]:
        # Scan with filter. Fine at this scale; switch to a GSI on
        # delete_status if the table grows large.
        items = []
        try:
            response = self.table.scan(
                FilterExpression=Attr('delete_status').eq('pending') & Attr('downloaded_at').lt(cutoff)
            )
            items.extend(response.get('Items', []))
            while 'LastEvaluatedKey' in response:
                response = self.table.scan(
                    FilterExpression=Attr('delete_status').eq('pending') & Attr('downloaded_at').lt(cutoff),
                    ExclusiveStartKey=response['LastEvaluatedKey'],
                )
                items.extend(response.get('Items', []))

            return items
        except ClientError as e:
            raise ScanTableError(f"Scan Table error: {e}")
    
    def update_records_status(self, partial_key: str, update_exp: str, attr_values: Dict):

        try:
            self.table.update_item(
                Key={'recording_id': partial_key},
                UpdateExpression=update_exp,
                ExpressionAttributeValues=attr_values,
            )
        except ClientError as e:
            raise UpdateTableError(f"Update Table error: {e}")