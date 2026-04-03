import asyncio
import hashlib
import json
import time
from collections import OrderedDict
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

try:
    from redis.asyncio import Redis as AsyncRedis
except Exception:  # pragma: no cover - optional dependency at runtime
    AsyncRedis = None  # type: ignore[assignment]


class InMemoryTTLCache:
    """Small async-safe in-memory TTL cache with LRU eviction."""

    def __init__(self, max_items: int):
        self.max_items = max_items
        self._store: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        now = time.time()
        async with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            value, expires_at = item
            if expires_at <= now:
                self._store.pop(key, None)
                return None
            self._store.move_to_end(key)
            return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = time.time() + ttl_seconds
        async with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
            self._store[key] = (value, expires_at)
            while len(self._store) > self.max_items:
                self._store.popitem(last=False)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)


class CacheService:
    """
    Redis-backed cache with in-memory fallback.
    Uses per-user corpus versioning for cheap invalidation.
    """

    def __init__(self):
        self._memory = InMemoryTTLCache(max_items=settings.cache_memory_max_items)
        self._redis: Any = None
        self._redis_ready = False

    async def _get_redis(self) -> Any | None:
        if self._redis_ready:
            return self._redis
        self._redis_ready = True

        if not settings.redis_url or AsyncRedis is None:
            return None

        try:
            self._redis = AsyncRedis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("cache_backend", backend="redis")
        except Exception as exc:
            self._redis = None
            logger.warning("cache_backend_fallback", backend="memory", error=str(exc))
        return self._redis

    async def get(self, key: str) -> str | None:
        redis_client = await self._get_redis()
        if redis_client:
            try:
                return await redis_client.get(key)
            except Exception as exc:
                logger.warning("cache_get_redis_failed", error=str(exc))
        return await self._memory.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        redis_client = await self._get_redis()
        if redis_client:
            try:
                await redis_client.set(key, value, ex=ttl_seconds)
                return
            except Exception as exc:
                logger.warning("cache_set_redis_failed", error=str(exc))
        await self._memory.set(key, value, ttl_seconds)

    async def delete(self, key: str) -> None:
        redis_client = await self._get_redis()
        if redis_client:
            try:
                await redis_client.delete(key)
            except Exception as exc:
                logger.warning("cache_delete_redis_failed", error=str(exc))
        await self._memory.delete(key)

    def embedding_key(self, text: str, model: str) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        return f"emb:{model}:{digest}"

    async def get_user_corpus_version(self, user_id: str) -> int:
        key = f"rag:corpus_ver:{user_id}"
        raw = await self.get(key)
        if raw is None:
            await self.set(key, "1", ttl_seconds=settings.cache_corpus_version_ttl_seconds)
            return 1
        try:
            return int(raw)
        except ValueError:
            return 1

    async def bump_user_corpus_version(self, user_id: str) -> int:
        key = f"rag:corpus_ver:{user_id}"
        redis_client = await self._get_redis()
        if redis_client:
            try:
                value = await redis_client.incr(key)
                await redis_client.expire(key, settings.cache_corpus_version_ttl_seconds)
                return int(value)
            except Exception as exc:
                logger.warning("cache_bump_redis_failed", error=str(exc))

        current = await self.get_user_corpus_version(user_id)
        next_value = current + 1
        await self.set(key, str(next_value), ttl_seconds=settings.cache_corpus_version_ttl_seconds)
        return next_value

    async def make_query_response_key(
        self,
        *,
        user_id: str,
        query: str,
        top_k: int,
        document_ids: list[str] | None,
        filters: dict[str, Any] | None,
    ) -> str:
        version = await self.get_user_corpus_version(user_id)
        normalized_docs = ",".join(sorted(document_ids or []))
        fingerprint = json.dumps(
            {
                "q": query.strip(),
                "k": top_k,
                "d": normalized_docs,
                "f": filters or {},
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        digest = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
        return f"rag:resp:{user_id}:v{version}:{digest}"

    @staticmethod
    def dumps_json(data: Any) -> str:
        return json.dumps(data, separators=(",", ":"), ensure_ascii=True)
