import math
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.services.cache_service import CacheService

settings = get_settings()


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class RateLimiterService:
    """Per-user fixed-window rate limiter (Redis-backed, memory fallback)."""

    def __init__(self, cache_service: CacheService):
        self.cache_service = cache_service

    async def check(self, *, user_id: str, scope: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        window_end = window_start + window_seconds
        retry_after = max(1, window_end - now)
        key = f"ratelimit:{scope}:{user_id}:{window_start}"

        redis_client = await self.cache_service._get_redis()  # noqa: SLF001
        if redis_client:
            current = int(await redis_client.incr(key))
            if current == 1:
                await redis_client.expire(key, window_seconds)
            remaining = max(0, limit - current)
            return RateLimitResult(
                allowed=current <= limit,
                limit=limit,
                remaining=remaining,
                retry_after_seconds=retry_after,
            )

        # Fallback path (non-atomic but safe enough for single-process mode)
        raw = await self.cache_service.get(key)
        current = int(raw) if raw else 0
        current += 1
        await self.cache_service.set(key, str(current), ttl_seconds=window_seconds)
        remaining = max(0, limit - current)
        return RateLimitResult(
            allowed=current <= limit,
            limit=limit,
            remaining=remaining,
            retry_after_seconds=retry_after,
        )
