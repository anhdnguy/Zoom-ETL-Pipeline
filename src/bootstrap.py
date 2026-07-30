import redis

from src.clients.zoom_token import RedisTokenStore, RedisLock, ZoomTokenProvider
from src.clients.zoom_client import ZoomClient
from src.config import AppConfig

def build_zoom_client() -> ZoomClient:
    r = redis.Redis(
        host=AppConfig.redis_host,
        port=AppConfig.redis_port,
        decode_responses=False,
    )

    store = RedisTokenStore(r, key="zoom:oauth:access_token")
    lock = RedisLock(r, lock_key="zoom:oauth:refresh_lock", ttl_seconds=30)

    provider = ZoomTokenProvider(
        store=store,
        lock=lock,
        oauth_token_url=AppConfig.zoom_oauth_token_url,
        client_id=AppConfig.zoom_client_id,
        client_secret=AppConfig.zoom_client_secret,
        account_id=AppConfig.zoom_account_id,
        skew_seconds=60
    )

    return ZoomClient(
        config=AppConfig,
        token_provider=provider
    )