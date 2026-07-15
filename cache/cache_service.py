"""Cache abstraction layer. Wraps Redis with simple get/set/delete/exists/expire/ttl/clear."""
import json
import logging
from typing import Any, Optional

from cache.redis_client import get_redis
from cache.metrics import metrics
from config.settings import settings

logger = logging.getLogger(__name__)


async def get(key: str) -> Optional[Any]:
    """Get a cached value by key. Returns None on miss or error."""
    client = get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            metrics.record_miss()
            return None
        metrics.record_hit()
        return json.loads(raw)
    except Exception:
        metrics.record_error()
        logger.debug("Cache get error key=%s", key, exc_info=True)
        return None


async def set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set a cached value. Returns True on success."""
    client = get_redis()
    if client is None:
        return False
    try:
        ttl = ttl or settings.redis_default_ttl
        await client.set(key, json.dumps(value), ex=ttl)
        metrics.record_write()
        return True
    except Exception:
        metrics.record_error()
        logger.debug("Cache set error key=%s", key, exc_info=True)
        return False


async def delete(key: str) -> bool:
    """Delete a cached key. Returns True if key existed."""
    client = get_redis()
    if client is None:
        return False
    try:
        result = await client.delete(key)
        if result > 0:
            metrics.record_delete()
        return result > 0
    except Exception:
        metrics.record_error()
        logger.debug("Cache delete error key=%s", key, exc_info=True)
        return False


async def exists(key: str) -> bool:
    """Check if a key exists."""
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.exists(key))
    except Exception:
        metrics.record_error()
        return False


async def expire(key: str, ttl: int) -> bool:
    """Set expiration on an existing key."""
    client = get_redis()
    if client is None:
        return False
    try:
        return bool(await client.expire(key, ttl))
    except Exception:
        metrics.record_error()
        return False


async def ttl(key: str) -> int:
    """Return remaining TTL in seconds. -1 = no expiry, -2 = missing, -3 = error."""
    client = get_redis()
    if client is None:
        return -3
    try:
        return await client.ttl(key)
    except Exception:
        metrics.record_error()
        return -3


async def clear(namespace: Optional[str] = None) -> int:
    """Clear keys. If namespace given, clears only that prefix. Returns count deleted."""
    client = get_redis()
    if client is None:
        return 0
    try:
        if namespace:
            pattern = f"tripplanner:{namespace}:*"
        else:
            pattern = "tripplanner:*"
        keys = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            metrics.record_delete()
        return len(keys)
    except Exception:
        metrics.record_error()
        logger.debug("Cache clear error namespace=%s", namespace, exc_info=True)
        return 0
