from src.clients.zoom_client import ZoomClient
from src.services.retry import RetryExecutor

from src.utils.logger import setup_logger
from src.clients.zoom_exceptions import (
    ZoomNotFoundError
)

from typing import List, Dict

logger = setup_logger(__name__)

class RecordingService:
    def __init__(self, client: ZoomClient, retry: RetryExecutor):
        self.client = client
        self.retry = retry

    def delete_recordings(self, group: List[Dict]):
        for item in group:
            try:
                self.retry.run(
                    lambda mid=item['meeting_uuid']: self.client.delete_recording_files(mid)
                )
                logger.info(f"Deleted Zoom recordings for meeting {item['meeting_uuid']}")
                item['status'] = 'deleted'
            except ZoomNotFoundError as e:
                logger.warning(
                    f"Recordings for meeting {item['meeting_uuid']} already gone from Zoom "
                    f"(deleted outside pipeline) — marking deleted_external"
                )
                item['status'] = 'deleted_external'
        
        return group
        