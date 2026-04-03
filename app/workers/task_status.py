"""Read Celery task state for API responses."""

from celery.result import AsyncResult

from app.workers.celery_app import celery_app


def get_celery_task_state(task_id: str | None) -> str | None:
    if not task_id:
        return None
    try:
        return AsyncResult(task_id, app=celery_app).state
    except Exception:
        return None
