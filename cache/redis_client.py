"""Singleton async Redis client with lazy init and graceful failure."""
import logging
from typing import Optional

from redis.asyncio import Redis, ConnectionPool

from config.settings import settings

logger = logging.getLogger(__name__)

_client: Optional[Redis] = None


def get_redis() -> Optional[Redis]:
    """Return the singleton Redis client, or None if Redis is disabled/unreachable."""
    global _client
    if not settings.redis_enabled:
        return None
    if _client is None:
        _client = _create_client()
    return _client


def _create_client() -> Redis:
    # ponytail: force IPv4 for localhost to avoid ::1 → 127.0.0.1 fallback timeout
    host = "127.0.0.1" if settings.redis_host == "localhost" else settings.redis_host
    pool = ConnectionPool(
        host=host,
        port=settings.redis_port,
        db=settings.redis_db,
        password=settings.redis_password or None,
        decode_responses=True,
        max_connections=10,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    client = Redis(connection_pool=pool)
    logger.info("Redis client created (%s:%s db=%s)", settings.redis_host, settings.redis_port, settings.redis_db)
    return client


async def ping_redis() -> bool:
    """Verify Redis connectivity. Returns False on failure, never raises."""
    client = get_redis()
    if client is None:
        return False
    try:
        return await client.ping()
    except Exception as e:
        logger.warning("Redis ping failed: %s: %s", type(e).__name__, e)
        return False


async def close_redis():
    """Gracefully close the Redis connection."""
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
