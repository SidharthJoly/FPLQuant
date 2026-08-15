import logging
from typing import cast

import redis
from redis.exceptions import RedisError

from fplquant.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client


def set_client(client: redis.Redis) -> None:
    """Test hook: inject a fake/mock Redis client instead of a real connection."""
    global _client
    _client = client


def cache_get(key: str) -> str | None:
    """Returns None on a cache miss *or* if Redis is unreachable — callers
    can't tell the difference, and shouldn't need to: either way, they should
    fall through to computing the value fresh. A cache is never allowed to be
    a hard dependency for correctness.
    """
    try:
        return cast(str | None, get_client().get(key))
    except RedisError:
        logger.warning("Redis unavailable, skipping cache read for key=%s", key)
        return None


def cache_set(key: str, value: str, ttl_seconds: int) -> None:
    try:
        get_client().set(key, value, ex=ttl_seconds)
    except RedisError:
        logger.warning("Redis unavailable, skipping cache write for key=%s", key)
