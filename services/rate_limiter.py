"""Application-level API rate limiting using Redis.

Uses get_redis() directly for atomic INCR/EXISTS/DELETE operations.
Fails open: if Redis is unavailable, requests pass through.
"""

import logging

from fastapi import HTTPException, status

from cache.cache_keys import CacheKeys
from cache.redis_client import get_redis
from config.settings import settings

logger = logging.getLogger(__name__)


async def _incr_with_ttl(key: str, ttl: int) -> int:
    """Atomically increment a counter. Sets TTL on first creation."""
    client = get_redis()
    if client is None:
        return 0
    count = await client.incr(key)
    if count == 1:
        await client.expire(key, ttl)
    return count


async def _is_locked(key: str) -> bool:
    client = get_redis()
    if client is None:
        return False
    return bool(await client.exists(key))


async def _set_lock(key: str, ttl: int) -> None:
    client = get_redis()
    if client is None:
        return
    await client.set(key, "1", ex=ttl)


async def _delete_keys(*keys: str) -> None:
    client = get_redis()
    if client is None:
        return
    existing = [k for k in keys if await client.exists(k)]
    if existing:
        await client.delete(*existing)


def _too_many(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


# ── Login ──────────────────────────────────────────────────────────────

async def check_login_rate_limit(email: str) -> None:
    """Raise 429 if login is locked for this email."""
    if not settings.rate_limit_enabled:
        return
    if await _is_locked(CacheKeys.login_lock(email)):
        raise _too_many(
            "Too many failed login attempts. Please try again after 25 hours or reset your password."
        )


async def record_login_failure(email: str) -> None:
    """Increment failure counter; lock if max reached."""
    if not settings.rate_limit_enabled:
        return
    ttl = settings.login_lock_hours * 3600
    count = await _incr_with_ttl(CacheKeys.login(email), ttl)
    if count >= settings.login_max_attempts:
        await _set_lock(CacheKeys.login_lock(email), ttl)


async def reset_login_failures(email: str) -> None:
    """Clear failure counter and lock (called on success or password reset)."""
    if not settings.rate_limit_enabled:
        return
    await _delete_keys(CacheKeys.login(email), CacheKeys.login_lock(email))


# ── Registration ───────────────────────────────────────────────────────

async def check_register_rate_limit(email: str) -> None:
    """Raise 429 if registration is locked for this email."""
    if not settings.rate_limit_enabled:
        return
    if await _is_locked(CacheKeys.register_lock(email)):
        raise _too_many(
            "Too many registration attempts. Please try again after 24 hours."
        )


async def record_register_failure(email: str) -> None:
    """Increment failure counter; lock if max reached."""
    if not settings.rate_limit_enabled:
        return
    ttl = settings.register_lock_hours * 3600
    count = await _incr_with_ttl(CacheKeys.register(email), ttl)
    if count >= settings.register_max_attempts:
        await _set_lock(CacheKeys.register_lock(email), ttl)


async def reset_register_failures(email: str) -> None:
    """Clear registration failure counter (called on success)."""
    if not settings.rate_limit_enabled:
        return
    await _delete_keys(CacheKeys.register(email))


# ── Trip failure ───────────────────────────────────────────────────────

async def check_trip_failure_rate_limit(user_id: str) -> None:
    """Raise 429 if trip planning is locked due to repeated failures."""
    if not settings.rate_limit_enabled:
        return
    if await _is_locked(CacheKeys.trip_failure_lock(user_id)):
        raise _too_many(
            "Trip planning failed multiple times. Please wait 20 minutes before trying again."
        )


async def record_trip_failure(user_id: str) -> None:
    """Increment failure counter; lock if max reached."""
    if not settings.rate_limit_enabled:
        return
    ttl = settings.trip_failure_lock_minutes * 60
    count = await _incr_with_ttl(CacheKeys.trip_failure(user_id), ttl)
    if count >= settings.trip_failure_max_attempts:
        await _set_lock(CacheKeys.trip_failure_lock(user_id), ttl)


async def reset_trip_failures(user_id: str) -> None:
    """Clear failure counter and lock (called on success)."""
    if not settings.rate_limit_enabled:
        return
    await _delete_keys(CacheKeys.trip_failure(user_id), CacheKeys.trip_failure_lock(user_id))


# ── Daily trip quota ───────────────────────────────────────────────────

async def check_trip_quota(user_id: str) -> None:
    """Raise 429 if daily successful trip limit is reached."""
    if not settings.rate_limit_enabled:
        return
    client = get_redis()
    if client is None:
        return
    raw = await client.get(CacheKeys.trip_success(user_id))
    if raw is not None and int(raw) >= settings.trip_success_daily_limit:
        raise _too_many(
            "You have reached your daily trip planning quota. Please try again after 24 hours."
        )


async def record_trip_success(user_id: str) -> None:
    """Increment success counter with rolling window TTL."""
    if not settings.rate_limit_enabled:
        return
    ttl = settings.trip_success_window_hours * 3600
    await _incr_with_ttl(CacheKeys.trip_success(user_id), ttl)


async def reset_trip_quota(user_id: str) -> None:
    """Clear success counter."""
    if not settings.rate_limit_enabled:
        return
    await _delete_keys(CacheKeys.trip_success(user_id))
