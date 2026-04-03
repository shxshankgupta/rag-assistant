import asyncio
import json
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.cache_service import CacheService

settings = get_settings()
logger = get_logger(__name__)

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


class EmbeddingService:
    """Local embedding service using sentence-transformers."""

    def __init__(self, cache_service: CacheService | None = None):
        self.model = get_model()
        self.dimension = settings.embedding_dimension
        self.cache_service = cache_service

    async def embed_texts(self, texts: list[str]) -> np.ndarray:
        """Embed multiple texts (runs in thread to avoid blocking)."""
        if not texts:
            return np.empty((0, self.dimension), dtype=np.float32)

        def _encode():
            return self.model.encode(
                texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=False,  # FAISS handles normalization
            )

        embeddings = await asyncio.to_thread(_encode)
        arr = embeddings.astype(np.float32)

        logger.debug("embeddings_created_local", count=len(texts), shape=arr.shape)
        return arr

    async def embed_query(self, text: str) -> np.ndarray:
        if self.cache_service:
            cache_key = self.cache_service.embedding_key(text, "local")
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
            cache_key = self.cache_service.embedding_key(text, "local")
            await self.cache_service.set(
                cache_key,
                json.dumps(query_embedding.tolist(), separators=(",", ":")),
                ttl_seconds=settings.cache_embedding_ttl_seconds,
            )

        return query_embedding