from celery import Celery

from app.core.config import get_settings

settings = get_settings()

broker = settings.celery_broker_url or settings.redis_url or "redis://localhost:6379/0"
backend = settings.celery_result_backend or settings.redis_url or broker

celery_app = Celery(
    "rag_assistant",
    broker=broker,
    backend=backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
