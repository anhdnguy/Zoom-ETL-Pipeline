import time
import logging
from typing import Callable, TypeVar

from src.clients.zoom_exceptions import (
    ZoomRateLimitError,
    ZoomServerError,
)

T = TypeVar("T")

class RetryExecutor:
    def __init__(self, max_retries: int, logger: logging.Logger):
        self.max_retries = max_retries
        self.logger = logger

    def run(self, fn: Callable[[], T]) -> T:
        for attempt in range(self.max_retries):
            try:
                return fn()
            except ZoomRateLimitError as e:
                self._handle_rate_limit(e, attempt)
            except ZoomServerError:
                self._handle_server_error(attempt)
        raise RuntimeError("Exhausted retries")

    def _handle_rate_limit(self, e: ZoomRateLimitError, attempt: int):
        if attempt == self.max_retries - 1:
            raise
        self.logger.warning(
            f"Zoom rate limit hit. Retry after {e.retry_after}. Current attempt: {attempt}"
        )
        time.sleep(e.retry_after)

    def _handle_server_error(self, attempt: int):
        if attempt == self.max_retries - 1:
            raise
        delay = 2 ** attempt
        self.logger.warning(
            f"Zoom server error, backing off. Delay after {delay}. Current attempt: {attempt}"
        )
        time.sleep(delay)
