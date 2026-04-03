from fastapi import APIRouter

from app.api.routes import auth, documents, query, health

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(documents.router, prefix="/api/v1")
api_router.include_router(query.router, prefix="/api/v1")
