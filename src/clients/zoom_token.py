# src/clients/token_provider.py
import json
import time
import secrets
from dataclasses import dataclass
from typing import Optional

import redis
import requests

from src.utils.logger import setup_logger

logger = setup_logger(__name__)

@dataclass(frozen=True)
class TokenPayload:
    access_token: str
    expires_at: int  # unix epoch seconds


class RedisTokenStore:
    def __init__(self, redis_client: redis.Redis, key: str):
        self.r = redis_client
        self.key = key

    def get(self) -> Optional[TokenPayload]:
        raw = self.r.get(self.key)
        if not raw:
            return None
        data = json.loads(raw)
        return TokenPayload(
            access_token=data["access_token"],
            expires_at=int(data["expires_at"]),
        )

    def set(self, payload: TokenPayload) -> None:
        # Store with TTL so Redis automatically clears it when expired.
        ttl = max(payload.expires_at - int(time.time()), 1)
        self.r.set(
            self.key,
            json.dumps({"access_token": payload.access_token, "expires_at": payload.expires_at}),
            ex=ttl,
        )


class RedisLock:
    def __init__(self, redis_client: redis.Redis, lock_key: str, ttl_seconds: int = 30):
        self.r = redis_client
        self.lock_key = lock_key
        self.ttl = ttl_seconds
        self._token = None

    def acquire(self) -> bool:
        token = secrets.token_urlsafe(16)
        ok = self.r.set(self.lock_key, token, nx=True, ex=self.ttl)
        if ok:
            self._token = token
            return True
        return False

    def release(self) -> None:
        if not self._token:
            return
        lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
          return redis.call("del", KEYS[1])
        else
          return 0
        end
        """
        self.r.eval(lua, 1, self.lock_key, self._token)
        self._token = None


class ZoomTokenProvider:
    def __init__(
        self,
        store: RedisTokenStore,
        lock: RedisLock,
        *,
        oauth_token_url: str,
        client_id: str,
        client_secret: str,
        account_id: str,
        skew_seconds: int = 60,
        timeout_seconds: int = 15,
        wait_seconds: float = 3.0,
    ):
        self.store = store
        self.lock = lock
        self.oauth_token_url = oauth_token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_id = account_id
        self.skew = skew_seconds
        self.timeout = timeout_seconds
        self.wait_seconds = wait_seconds

    def get_access_token(self) -> str:
        logger.info("Attempt to get access token")
        now = int(time.time())

        cached = self.store.get()
        if cached and now < (cached.expires_at - self.skew):
            logger.info("Access token found and is still usable")
            return cached.access_token

        logger.info("Access token is unusable, attempt to acquire lock")
        # Try to acquire lock; if we fail, someone else is refreshing.
        if not self.lock.acquire():
            logger.info("Lock cannot be acquired, someone else might be refreshing the token.")
            deadline = time.time() + self.wait_seconds
            logger.info(f"Wait for {deadline}.")
            while time.time() < deadline:
                time.sleep(0.25)
                cached = self.store.get()
                if cached and int(time.time()) < (cached.expires_at - self.skew):
                    return cached.access_token
            raise RuntimeError("Token refresh in progress but no token became available")

        try:
            logger.info("Lock is acquired and attempt to refresh the token.")
            # Double-check after acquiring lock (avoid duplicate refresh).
            cached = self.store.get()
            if cached and int(time.time()) < (cached.expires_at - self.skew):
                return cached.access_token

            payload = self._refresh()
            self.store.set(payload)
            return payload.access_token
        finally:
            logger.info("Lock is released.")
            self.lock.release()

    def _refresh(self) -> TokenPayload:
        logger.info("Attempt to refresh token.")
        resp = requests.post(
            self.oauth_token_url,
            auth=(self.client_id, self.client_secret),
            data={"grant_type": "account_credentials", "account_id": self.account_id},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        access_token = data["access_token"]
        expires_in = int(data["expires_in"])
        expires_at = int(time.time()) + expires_in
        return TokenPayload(access_token=access_token, expires_at=expires_at)
