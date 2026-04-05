import asyncio
import hashlib
import json
import re

import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.cache_service import CacheService

settings = get_settings()
logger = get_logger(__name__)

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    lowered = text.lower()
    words = TOKEN_RE.findall(lowered)
    if not words:
        return ["__empty__"]

    joined = "".join(words)
    trigrams = [joined[i : i + 3] for i in range(max(0, len(joined) - 2))]
    return words + trigrams


class EmbeddingService:
    """Deterministic local embedding service with no runtime model downloads."""

    def __init__(self, cache_service: CacheService | None = None):
        self.dimension = settings.embedding_dimension
        self.model_name = settings.embedding_model_name
        self.cache_service = cache_service

    def _embed_single(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)

        for token in _tokenize(text):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = 1.25 if len(token) > 3 else 1.0
            vector[index] += sign * weight

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm

        return vector

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts in a worker thread to avoid blocking the event loop."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        def _encode() -> np.ndarray:
            return np.vstack([self._embed_single(text) for text in texts])

        embeddings = await asyncio.to_thread(_encode)
        arr = embeddings.astype(np.float32)

        logger.debug(
            "embeddings_created_local",
            count=len(texts),
            dimension=self.dimension,
            shape=arr.shape,
        )
        return arr

    async def embed_query(self, text: str) -> np.ndarray:
        if self.cache_service:
            cache_key = self.cache_service.embedding_key(text, self.model_name)
            cached = await self.cache_service.get(cache_key)
            if cached:
                try:
                    values = json.loads(cached)
                    return np.array(values, dtype=np.float32)
                except Exception:
                    await self.cache_service.delete(cache_key)

        embeddings = await self.embed_texts([text])
        query_embedding = embeddings[0]

        if self.cache_service:
            cache_key = self.cache_service.embedding_key(text, self.model_name)
            await self.cache_service.set(
                cache_key,
                json.dumps(query_embedding.tolist(), separators=(",", ":")),
                ttl_seconds=settings.cache_embedding_ttl_seconds,
            )

        return query_embedding
