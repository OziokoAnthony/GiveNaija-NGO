import json
import logging
from typing import Any, Optional
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis client pool
try:
    redis_client = redis.Redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
    )
except Exception as e:
    logger.warning(f"Could not initialize Redis client: {e}")
    redis_client = None


def get_cache(key: str) -> Optional[Any]:
    """Retrieve and deserialize JSON value from Redis."""
    if not redis_client:
        return None
    try:
        val = redis_client.get(key)
        if val:
            return json.loads(val)
    except Exception as e:
        logger.warning(f"Redis get error for key '{key}': {e}")
    return None


def set_cache(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """Serialize and store JSON value in Redis with TTL."""
    if not redis_client:
        return
    try:
        serialized = json.dumps(value, default=str)
        redis_client.set(key, serialized, ex=ttl_seconds)
    except Exception as e:
        logger.warning(f"Redis set error for key '{key}': {e}")


def invalidate_cache(pattern: str) -> None:
    """Invalidate all keys matching a glob pattern."""
    if not redis_client:
        return
    try:
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Redis invalidate error for pattern '{pattern}': {e}")
