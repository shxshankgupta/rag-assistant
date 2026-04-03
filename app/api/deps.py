from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import UnauthorizedError
from app.core.config import get_settings
from app.core.exceptions import RateLimitError
from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.embedding_service import EmbeddingService
from app.services.cache_service import CacheService
from app.services.vector_store import VectorStoreService
from app.services.document_service import DocumentService
from app.services.rag_service import RAGService
from app.services.rate_limiter_service import RateLimiterService
from app.services.user_service import UserService

settings = get_settings()
logger = get_logger(__name__)


# ------------------------------------------------------------------ #
# Singletons (module-level, created once per worker process)
# ------------------------------------------------------------------ #

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(get_cache_service())


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()


@lru_cache(maxsize=1)
def get_cache_service() -> CacheService:
    return CacheService()


@lru_cache(maxsize=1)
def get_rate_limiter_service() -> RateLimiterService:
    return RateLimiterService(get_cache_service())


# ------------------------------------------------------------------ #
# Per-request service factories
# ------------------------------------------------------------------ #

def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


def get_document_service(
    db: AsyncSession = Depends(get_db),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    cache_svc: CacheService = Depends(get_cache_service),
) -> DocumentService:
    return DocumentService(db, embedding_svc, vector_store, cache_svc)


def get_rag_service(
    db: AsyncSession = Depends(get_db),
    embedding_svc: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStoreService = Depends(get_vector_store),
    cache_svc: CacheService = Depends(get_cache_service),
) -> RAGService:
    return RAGService(db, embedding_svc, vector_store, cache_svc)


# ------------------------------------------------------------------ #
# Auth dependency
# ------------------------------------------------------------------ #

async def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate JWT from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")

    token = authorization.removeprefix("Bearer ").strip()

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        user_id: str = payload.get("sub", "")
    except JWTError as e:
        raise UnauthorizedError(f"Invalid token: {e}")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise UnauthorizedError("User not found")
    if not user.is_active:
        raise UnauthorizedError("Account is disabled")

    return user


async def get_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        from app.core.exceptions import ForbiddenError
        raise ForbiddenError("Superuser access required")
    return current_user


# Convenient type aliases for route signatures
CurrentUser = Annotated[User, Depends(get_current_user)]


def _rate_limit_dependency(scope: str, limit: int):
    async def _checker(
        current_user: CurrentUser,
        limiter: RateLimiterService = Depends(get_rate_limiter_service),
    ) -> None:
        result = await limiter.check(
            user_id=current_user.id,
            scope=scope,
            limit=limit,
            window_seconds=60,
        )
        if not result.allowed:
            logger.warning(
                "rate_limit_exceeded",
                user_id=current_user.id,
                scope=scope,
                limit=result.limit,
                retry_after_seconds=result.retry_after_seconds,
            )
            raise RateLimitError(
                detail=f"Rate limit exceeded for {scope}: {limit} requests/minute",
                retry_after_seconds=result.retry_after_seconds,
                limit=result.limit,
                remaining=result.remaining,
            )

    return _checker


enforce_api_rate_limit = _rate_limit_dependency("api", settings.api_rate_limit_per_minute)
enforce_query_rate_limit = _rate_limit_dependency("query", settings.query_rate_limit_per_minute)
