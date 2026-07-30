# app/zoom_client.py
import requests
from typing import BinaryIO, Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from app.exceptions import (
    ZoomAuthenticationError,
    ZoomRecordingNotFoundError,
    ZoomRateLimitError,
    ZoomDownloadError
)
from app.logger import setup_logger
from app.config import Config

logger = setup_logger(__name__)

class ZoomClient:
    """Client for interacting with Zoom API"""
    
    def __init__(self):
        self.base_url = Config.ZOOM_API_BASE_URL
        self.session = self._create_session()
        self._access_token = None
    
    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic for network failures.
        """
        session = requests.Session()
        
        # Retry strategy for network-level failures
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # Wait 1s, 2s, 4s between retries
            status_forcelist=[500, 502, 503, 504],  # Retry on server errors
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(self, method: str, url: str, download_token: str, **kwargs) -> requests.Response:
        """
        Make authenticated request to Zoom API with error handling.
        
        Raises:
            ZoomAuthenticationError: Invalid/expired token
            ZoomRateLimitError: Rate limit hit
            ZoomDownloadError: Other API errors
        """
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f'Bearer {download_token}'
        kwargs['headers'] = headers
        
        try:
            response = self.session.request(method, url, **kwargs)
            
            # Handle specific HTTP status codes
            if response.status_code == 401:
                # Token expired - clear cache and retry once
                logger.warning("Access token expired, refreshing...")
                self._access_token = None
                raise ZoomAuthenticationError("Access token expired or invalid")
            
            elif response.status_code == 404:
                raise ZoomRecordingNotFoundError(f"Recording not found: {url}")
            
            elif response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited. Retry after {retry_after}s")
                raise ZoomRateLimitError(retry_after)
            
            elif response.status_code >= 400:
                raise ZoomDownloadError(
                    f"Zoom API error {response.status_code}: {response.text}"
                )
            
            response.raise_for_status()
            return response
        
        except requests.exceptions.RequestException as e:
            raise ZoomDownloadError(f"Network error: {str(e)}")
    
    def download_recording(
        self, 
        download_url: str,
        download_token: str,
        file_obj: BinaryIO
    ) -> int:
        """
        Download recording from Zoom and write to file-like object.
        
        Streams the download in chunks to avoid loading entire file in memory.
        
        Args:
            download_url: Direct download URL from Zoom
            file_obj: File-like object to write to (e.g., BytesIO, file, pipe)
        
        Returns:
            Total bytes downloaded
        
        Raises:
            ZoomDownloadError: If download fails
        """
        logger.info(f"Starting download from: {download_url}")
        
        try:
            # Stream download with timeout
            response = self._make_request(
                'GET',
                download_url,
                download_token,
                stream=True,  # Critical: stream large files
                timeout=(10, 300)  # (connect timeout, read timeout)
            )
            
            total_bytes = 0
            chunk_size = Config.DOWNLOAD_CHUNK_SIZE
            
            # Write chunks as they arrive
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:  # Filter out keep-alive chunks
                    file_obj.write(chunk)
                    total_bytes += len(chunk)
                    
                    # Log progress every 50 MB
                    if total_bytes % (50 * 1024 * 1024) < chunk_size:
                        logger.info(f"Downloaded {total_bytes / (1024*1024):.1f} MB...")
            
            logger.info(f"Download complete: {total_bytes / (1024*1024):.1f} MB")
            return total_bytes
        
        except Exception as e:
            logger.error(f"Download failed: {str(e)}")
            raise ZoomDownloadError(f"Failed to download recording: {str(e)}")

# Global instance
zoom_client = ZoomClient()