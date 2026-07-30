class ZoomError (Exception):
    """Base exception for all Zoom client errors"""
    pass


class ZoomAuthError(ZoomError):
    """Authentication or authorization failed (401 / 403)"""
    pass

class ZoomRateLimitError(ZoomError):
    """Zoom API rate limit exceeded (429)"""
    def __init__(self, retry_after: int | None = None):
        self.retry_after = retry_after

class ZoomNotFoundError(ZoomError):
    """Resource not found (404)"""
    pass

class ZoomBadRequestError(ZoomError):
    """Invalid request (400)"""
    def __init__(self, message: str | None = None, payload: dict | None = None):
        self.message = message
        self.payload = payload

class ZoomServerError(ZoomError):
    """Zoom internal server error (5xx)"""
    pass

class ZoomNetworkError(ZoomError):
    """Network or connection error"""
    pass

class ZoomWebinarRedirectError(ZoomError):
    def __init__(self, webinar_id: str):
        self.webinar_id = webinar_id
        super().__init__(f"Meeting refers to webinar {webinar_id}")