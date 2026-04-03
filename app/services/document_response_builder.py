"""Build API document payloads with optional Celery enrichment."""

from app.models.document import Document, DocumentStatus
from app.schemas.documents import DocumentResponse
from app.workers.task_status import get_celery_task_state


def processing_view(doc: Document, celery_state: str | None) -> str:
    if doc.status == DocumentStatus.READY:
        return "completed"
    if doc.status == DocumentStatus.FAILED:
        return "failed"
    if doc.status == DocumentStatus.PROCESSING:
        return "processing"
    if doc.status == DocumentStatus.PENDING:
        if celery_state in ("STARTED", "RETRY", "PROGRESS"):
            return "processing"
        return "queued"
    return "queued"


def document_to_response(doc: Document, *, include_celery_state: bool = False) -> DocumentResponse:
    celery_state = (
        get_celery_task_state(doc.celery_task_id) if include_celery_state and doc.celery_task_id else None
    )
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_name=doc.original_name,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        celery_task_id=doc.celery_task_id,
        celery_state=celery_state,
        processing_view=processing_view(doc, celery_state),
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
