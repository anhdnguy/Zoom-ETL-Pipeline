from src.clients.dynamodb_client import DynamoDBClient
from src.storage.s3_reader import S3Reader
from src.utils.logger import setup_logger
from src.storage.s3_exceptions import S3GetHeadObjectError

from typing import List, Dict
from datetime import datetime, timedelta, timezone

logger = setup_logger(__name__)

class DeleteServices:
    def __init__(self, client: DynamoDBClient, s3: S3Reader) -> List[Dict]:
        self.db_client = client
        self.s3 = s3

    def get_recordings(self, SAFETY_WINDOW_DAYS: int) -> List[Dict]:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=SAFETY_WINDOW_DAYS)).isoformat()

        eligible_recordings = self.db_client.scan_records(cutoff)

        return eligible_recordings
    
    def verify_s3_object(self, recordings: List[Dict]) -> List[Dict]:
        verified = []
        for rec in recordings:
            key = rec['s3_key_recording_file']
            try:
                head = self.s3.get_head_object(key)
            except S3GetHeadObjectError as e:
                logger.warning(f"S3 archive missing for {rec['recording_uuid']}, marking failed")
                self.db_client.update_records_status(
                    rec['recording_uuid'], 'SET delete_status = :s', {':s': 'failed'}
                )

            if head['ContentLength'] > 0:
                verified.append(rec)
            else:
                logger.warning(f"Zero-byte archive for {rec['recording_uuid']}, marking failed")
                self.db_client.update_records_status(
                    rec['recording_uuid'], 'SET delete_status = :s', {':s': 'failed'}
                )
        
        logger.info(f"{len(verified)}/{len(recordings)} recordings passed S3 verification")
        return verified

    def update_deleted_records(self, group: List[Dict]) -> None:
        for item in group:
            if item['status'] in ('deleted', 'deleted_external'):
                logger.info(f"Update {item['meeting_uuid']} recordings to {item['status']}")
                for rec in item['recording_ids']:
                    self.db_client.update_records_status(rec, 'SET delete_status = :s', {':s': item['status']})
            else:
                for rec in item['recording_ids']:
                    self.db_client.update_records_status(rec, 'ADD retry_count :one', {':one': 1})
