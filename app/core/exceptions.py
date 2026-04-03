# Make Any importable
from typing import Any  # noqa: E402

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base application error."""
    pass


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: Any = None):
        detail = f"{resource} not found"
        if identifier:
            detail += f": {identifier}"
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedError(AppError):
    def __init__(self, detail: str = "Not authenticated"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictError(AppError):
    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class ValidationError(AppError):
    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail
        )


class StorageError(AppError):
    def __init__(self, detail: str = "Storage operation failed"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail
        )


class RateLimitError(AppError):
    def __init__(
        self,
        detail: str = "Rate limit exceeded",
        retry_after_seconds: int = 60,
        limit: int | None = None,
        remaining: int | None = None,
    ):
        headers = {"Retry-After": str(retry_after_seconds)}
        if limit is not None:
            headers["X-RateLimit-Limit"] = str(limit)
        if remaining is not None:
            headers["X-RateLimit-Remaining"] = str(remaining)
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers=headers,
        )



