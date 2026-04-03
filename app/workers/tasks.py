"""Celery tasks for long-running work."""

import asyncio

from celery import Task
from openai import APIError, AuthenticationError, BadRequestError, PermissionDeniedError, RateLimitError

from app.core.logging import get_logger
from app.workers.celery_app import celery_app
from app.workers.document_pipeline import (
    NonRetryableProcessingError,
    _mark_failed,
    run_document_embedding_pipeline,
)

logger = get_logger(__name__)


def _is_non_retryable_openai_error(exc: Exception) -> bool:
    # These should fail the document immediately instead of looping retries.
    if isinstance(exc, (AuthenticationError, PermissionDeniedError, BadRequestError)):
        return True

    if isinstance(exc, RateLimitError):
        message = str(exc).lower()
        # Quota/billing exhaustion is not transient.
        if "insufficient_quota" in message or "exceeded your current quota" in message:
            return True

    return False


class DocumentEmbeddingTask(Task):
    """After all retries are exhausted, persist FAILED on the document."""

    max_retries = 5
    default_retry_delay = 30

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        doc_id = args[0] if args else None
        if doc_id:
            try:
                asyncio.run(_mark_failed(doc_id, str(exc)))
            except Exception as mark_err:
                logger.error(
                    "document_mark_failed_after_task_failure",
                    doc_id=doc_id,
                    error=str(mark_err),
                )
        super().on_failure(exc, task_id, args, kwargs, einfo)


@celery_app.task(bind=True, base=DocumentEmbeddingTask, name="app.workers.tasks.process_document_embedding")
def process_document_embedding(self, doc_id: str, user_id: str) -> None:
    try:
        asyncio.run(run_document_embedding_pipeline(doc_id, user_id))

    except NonRetryableProcessingError:
        raise

    except Exception as exc:
        if _is_non_retryable_openai_error(exc):
            logger.error(
                "document_embedding_non_retryable_failure",
                doc_id=doc_id,
                error=str(exc),
            )
            try:
                asyncio.run(_mark_failed(doc_id, str(exc)))
            except Exception as mark_err:
                logger.error(
                    "document_mark_failed_after_non_retryable_failure",
                    doc_id=doc_id,
                    error=str(mark_err),
                )
            raise NonRetryableProcessingError(str(exc)) from exc

        logger.warning(
            "document_embedding_retry",
            doc_id=doc_id,
            retry=self.request.retries,
            max_retries=self.max_retries,
            error=str(exc),
        )
        countdown = min(600, int(self.default_retry_delay * (2 ** self.request.retries)))
        raise self.retry(exc=exc, countdown=countdown)