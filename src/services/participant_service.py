from src.clients.zoom_client import ZoomClient
from src.services.retry import RetryExecutor

from src.transforms.participants import add_meeting_id, flatten_participant

from typing import List, Dict

class ParticipantService:
    def __init__(self, client: ZoomClient, retry: RetryExecutor):
        self.client = client
        self.retry = retry

    def fetch_meeting_participants(self, meeting_refs: List[Dict]) -> List[Dict]:
        results = []

        for ref in meeting_refs:
            user_id = ref.get("user_id")
            meeting_ids = ref.get("meeting_ids")
            for meeting_id in meeting_ids:
                participants = self.retry.run(
                    lambda mid=meeting_id: self.client.fetch_meeting_participants(mid)
                )

                participants_with_meeting_id = add_meeting_id(meeting_id, participants)
                results.append(participants_with_meeting_id)
        
        return flatten_participant(results)