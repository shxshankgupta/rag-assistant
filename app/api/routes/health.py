from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    version: str = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe — always returns 200 if the process is running."""
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.app_env,
    )


@router.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": f"Welcome to {settings.app_name}. Docs at /docs"}
