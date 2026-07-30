from src.clients.zoom_client import ZoomClient
from src.services.retry import RetryExecutor

from typing import List, Dict

from src.transforms.users import (
    extract_user_ids,
    split_users
)

class UserService:
    def __init__(self, client: ZoomClient, retry: RetryExecutor):
        self.client = client
        self.retry = retry

    def fetch_all_user_ids(self) -> List[List[str]]:
        users = self.retry.run(
            lambda: self.client.fetch_all_users()
        )
        
        lstEmails = extract_user_ids(users)

        return split_users(lstEmails, chunk_size=1000)
    
    def fetch_user_details(self, user_ids: List[str]) -> List[Dict]:
        results = []
        for user_id in user_ids:
            user_details = self.retry.run(
                lambda: self.client.fetch_user_details(user_id)
            )

            results.append(user_details)
        
        return results