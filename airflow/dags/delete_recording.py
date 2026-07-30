"""
Zoom Recording Deletion Pipeline
Deletes Zoom cloud recordings that were successfully downloaded to S3
at least 7 days ago. Groups recordings by meeting ID since Zoom's
DELETE /meetings/{meetingId}/recordings removes all recordings for a meeting.
"""

from airflow.sdk import dag, task
from datetime import datetime, timedelta
from typing import List, Dict

from src.utils.logger import setup_logger
from src.bootstrap import build_zoom_client
from src.services.recording_service import RecordingService
from src.clients.dynamodb_client import DynamoDBClient
from src.storage.s3_reader import S3Reader
from src.services.delete_service import DeleteServices
from src.services.retry import RetryExecutor
from src.config import AppConfig

logger = setup_logger(__name__)

SAFETY_WINDOW_DAYS = 6
CHUNK_SIZE = 100
MAX_RETRIES = AppConfig.max_retries

default_args = {
    'owner': 'Anh',
    'depends_on_past': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'start_date': datetime(2026, 3, 20),
}


@dag(
    'Zoom_Recording_Deletion',
    schedule='0 6 * * *',          # Daily at 6 AM — after the 4 AM ETL
    default_args=default_args,
    catchup=False,
    tags=['Zoom', 'cleanup'],
    description='Delete Zoom cloud recordings already archived to S3',
)
def delete_recordings():

    @task
    def get_eligible_recordings() -> List[Dict]:
        """
        Query DynamoDB for recordings with:
          - delete_status = 'pending'
          - downloaded_at older than SAFETY_WINDOW_DAYS
        """
        client = DynamoDBClient(AppConfig)
        s3 = S3Reader(AppConfig)
        service = DeleteServices(client, s3)
        return service.get_recordings(SAFETY_WINDOW_DAYS)

    @task
    def verify_s3_archives(recordings: List[Dict]) -> List[Dict]:
        """
        Safety check: only delete from Zoom if the S3 copy exists
        and is non-empty. Recordings failing verification are marked
        'failed' so they surface for investigation instead of retrying forever.
        """
        client = DynamoDBClient(AppConfig)
        s3 = S3Reader(AppConfig)
        service = DeleteServices(client, s3)
        return service.verify_s3_object(recordings)

    @task
    def group_by_meeting(recordings: List[Dict]) -> List[List[Dict]]:
        """
        Group recordings by meeting_uuid. Zoom's delete API removes ALL
        recordings for a meeting, so one API call covers every file.
        Returns: [{"meeting_uuid": ..., "recording_ids": [...]}, ...]
        """
        groups: Dict[str, List[str]] = {}
        for rec in recordings:
            groups.setdefault(rec['meeting_uuid'], []).append(rec['recording_id'])

        result = [
            {'meeting_uuid': m, 'recording_ids': ids, 'status': None}
            for m, ids in groups.items()
        ]
        logger.info(f"{len(recordings)} recordings grouped into {len(result)} meetings")
        return [result[i:i + CHUNK_SIZE] for i in range(0, len(result), CHUNK_SIZE)]

    @task
    def delete_meeting_recordings(group: List[Dict]) -> None:
        """
        Call Zoom DELETE /meetings/{meetingId}/recordings for one meeting
        """
        client = build_zoom_client()
        retry = RetryExecutor(MAX_RETRIES, logger)
        service = RecordingService(client, retry)
        return service.delete_recordings(group)

    @task
    def update_deleted_recordings(group: List[Dict]):
        client = DynamoDBClient(AppConfig)
        s3 = S3Reader(AppConfig)
        service = DeleteServices(client, s3)
        service.update_deleted_records(group)

    # ─── Flow ─────────────────────────────────────────────
    eligible = get_eligible_recordings()
    verified = verify_s3_archives(eligible)
    groups = group_by_meeting(verified)
    post_delete_groups = delete_meeting_recordings.expand(group=groups)
    update_deleted_recordings.expand(group=post_delete_groups)


delete_recordings()