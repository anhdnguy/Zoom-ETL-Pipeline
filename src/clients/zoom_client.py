import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Generator

from src.clients.zoom_token import ZoomTokenProvider
from src.config import AppConfig
from urllib.parse import quote

from requests.exceptions import HTTPError, RequestException
from src.clients.zoom_exceptions import (
    ZoomError,
    ZoomAuthError,
    ZoomRateLimitError,
    ZoomNotFoundError,
    ZoomBadRequestError,
    ZoomServerError,
    ZoomWebinarRedirectError
)

class ZoomClient:
    def __init__(self, config: AppConfig, token_provider: ZoomTokenProvider):
        self.config = config
        self.base_url = config.zoom_api_url
        self.DEFAULT_PAGE_SIZE = config.default_page_size
        self.token_provider = token_provider

    def _headers(self) -> Dict[str, str]:
        token = self.token_provider.get_access_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def _make_api_call (self, url: str, params: Dict = None, method: str = "GET") -> Dict:
        params = params or {}
        
        try:
            response = requests.request(method, url, headers=self._headers(), params=params)
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
        except HTTPError as e:
            status = e.response.status_code
            if status in (401, 403):
                raise ZoomAuthError() from e
            elif status == 429:
                retry_after = int(e.response.headers.get('Retry-After', 60))
                raise ZoomRateLimitError(retry_after) from e
            elif status == 404:
                raise ZoomNotFoundError() from e
            elif status == 400:
                try:
                    payload = e.response.json()
                except ValueError:
                    payload = {}
                message = payload.get("message", "")
                if "Can not access webinar info," in message:
                    webinar_id = message.split(", ")[1].strip()
                    raise ZoomWebinarRedirectError(webinar_id)
                raise ZoomBadRequestError(message, params) from e
            elif status >= 500:
                raise ZoomServerError() from e
            
            raise ZoomError(f"Unexpected HTTP error: {status}") from e
        
        except RequestException as e:
            raise ZoomError(f"Network error communicating with Zoom ({method} {url})") from e

    def _make_paginated_request(self, url: str, params: Dict = None) -> Generator[Dict, None, None]:
        """Helper method to handle paginated API requests."""
        params = params or {}
        while True:
            page = self._make_api_call(url, params)

            yield page

            next_page_token = page.get("next_page_token")
            if not next_page_token:
                break
            params["next_page_token"] = next_page_token

    def fetch_all_users(self, token: Optional[str] = None) -> List[str]:
        """Get all user IDs from the API."""
        user_emails = []
        for _status in {'active'}:
            url = f"{self.base_url}/users"
            params = {
                'page_size' : self.DEFAULT_PAGE_SIZE,
                'status' : _status
            }

            for page in self._make_paginated_request(url, params):
                user_emails.extend(page.get('users', []))
            
        return list(user_emails)
    
    def fetch_user_details(self, user_id: str, token: Optional[str]=None) -> Dict:
        """Get details for a specific user."""            
        url = f"{self.base_url}/users/{user_id}"

        response = self._make_api_call(url)
        return response
    
    def get_range(self, start: datetime, end: datetime) -> Generator[tuple[datetime, datetime], None, None]:
        """Generate date ranges in 30-day chunks."""
        curr = start
        date_difference = timedelta(days=30)
        while curr < end:
            yield curr, min(curr + date_difference, end)
            curr += date_difference

    def fetch_meetings(
        self,
        user_id: str,
        since_timestamp: datetime,
        token: Optional[str]=None
    ) -> List[Dict]:
        """Get meetings for a user since the specified timestamp."""
        url = f"{self.base_url}/report/users/{user_id}/meetings"

        lstMeetings = []
        for start, end in self.get_range(since_timestamp, datetime.today()):
            params = {
                'from': start.strftime('%Y-%m-%d'),
                'to':end.strftime('%Y-%m-%d'),
                'page_size': self.DEFAULT_PAGE_SIZE
            }

            for page in self._make_paginated_request(url, params):
                lstMeetings.extend(page.get('meetings', []))
        return lstMeetings
    
    def fetch_meeting_details(self, meeting_id: str, token: Optional[str]=None) -> Dict:
        """Get details for a specific meeting using past meeting endpoint."""
        encoded_meeting_id = quote(quote(meeting_id, safe=''), safe='')
        url = f"{self.base_url}/past_meetings/{encoded_meeting_id}"

        response = self._make_api_call(url)
        return response
    
    def fetch_webinar_details(self, webinar_id: str, token: Optional[str]=None) -> Dict:
        """Get details for a specific meeting using webinar endpoint."""
        url = f"{self.base_url}/webinars/{webinar_id}"

        response = self._make_api_call(url)
        return response
    
    def fetch_meeting_participants(self, meeting_id: str, token: Optional[str]=None) -> List[Dict]:
        """Get a list of participants of a meeting."""
        encoded_meeting_id = quote(quote(meeting_id, safe=''), safe='')
        url = f"{self.base_url}/past_meetings/{encoded_meeting_id}/participants"
        params = {'page_size': self.DEFAULT_PAGE_SIZE}
        
        participants = []
        for page in self._make_paginated_request(url, params):
            participants.extend(page.get('participants', []))

        return participants
    
    def delete_recording_files(self, meeting_uuid: str, token: Optional[str]=None) -> None:
        """Delete all of a meetings or webinars recording files"""
        encoded_meeting_id = quote(quote(meeting_uuid, safe=''), safe='')
        url = f"{self.base_url}/meetings/{encoded_meeting_id}/recordings"
        self._make_api_call(url, params=None, method="DELETE")
