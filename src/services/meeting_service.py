from src.clients.zoom_client import ZoomClient
from src.services.retry import RetryExecutor

from typing import List, Dict
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

from src.transforms.meetings import extract_meeting_ids

from src.clients.zoom_exceptions import (
    ZoomWebinarRedirectError
)

class MeetingService:
    def __init__(self, client: ZoomClient, retry: RetryExecutor):
        self.client = client
        self.retry = retry

    def fetch_user_meetings_since(self, user_ids: List[str], last_run_dt: datetime) -> List[Dict]:
        results = []
        for user_id in user_ids:
            meetings = self.retry.run(
                lambda mid=user_id: self.client.fetch_meetings(mid, last_run_dt)
            )
            if not meetings:
                continue

            meeting_ids = extract_meeting_ids(meetings)

            results.append({
                "user_id" : user_id,
                "meeting_ids": meeting_ids
            })
        
        return results
    
    def fetch_webinar_details(self, webinar_id: str) -> Dict:
        webinar_detail = self.retry.run(
            lambda: self.client.fetch_webinar_details(webinar_id)
        )
        return webinar_detail
    
    def fetch_meeting_details(self, meeting_refs: List[Dict]) -> List[Dict]:
        results = []
        for ref in meeting_refs:
            user_id = ref.get("user_id")
            meeting_ids = ref.get("meeting_ids")
            for meeting_id in meeting_ids:
                try:
                    meeting_detail = self.retry.run(
                        lambda mid=meeting_id: self.client.fetch_meeting_details(mid)
                    )
                except ZoomWebinarRedirectError as e:
                    logger.info(
                        f"Meeting {meeting_id} is a webinar, redirecting to {e.webinar_id}"
                    )
                    meeting_detail = self.fetch_webinar_details(e.webinar_id)

                results.append(meeting_detail)

        return results