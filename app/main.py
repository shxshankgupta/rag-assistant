from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import AsyncGenerator
from uuid import uuid4

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from app.api import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import get_logger, setup_logging
from app.db.session import init_db

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    logger.info("startup", app=settings.app_name, env=settings.app_env)
    await init_db()
    logger.info("database_ready")
    yield
    logger.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "Production-ready Retrieval-Augmented Generation (RAG) API. "
            "Upload PDFs, query with AI, get streamed answers."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def request_tracking_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id", uuid4().hex)
        start = perf_counter()
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        logger.info(
            "request_received",
            request_time=datetime.now(timezone.utc).isoformat(),
            client_ip=request.client.host if request.client else None,
            query_params=str(request.query_params) if request.query_params else "",
        )

        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            elapsed_ms = round((perf_counter() - start) * 1000, 2)
            logger.info(
                "request_completed",
                response_time=datetime.now(timezone.utc).isoformat(),
                response_latency_ms=elapsed_ms,
                status_code=response.status_code if response else 500,
            )
            if response:
                response.headers["X-Request-ID"] = request_id
            structlog.contextvars.clear_contextvars()

    # ------------------------------------------------------------------ #
    # CORS
    # ------------------------------------------------------------------ #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins_list,
        allow_origin_regex=settings.allowed_origin_regex or None,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # Exception handlers
    # ------------------------------------------------------------------ #

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "app_error",
            status=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "unhandled_error",
            error=str(exc),
            path=request.url.path,
            exc_info=True,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An internal server error occurred"},
        )

    # ------------------------------------------------------------------ #
    # Routes
    # ------------------------------------------------------------------ #
    app.include_router(api_router)

    return app


app = create_app()
