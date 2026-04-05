"""Build API document payloads."""

from app.models.document import Document, DocumentStatus
from app.schemas.documents import DocumentResponse


def processing_view(doc: Document) -> str:
    if doc.status == DocumentStatus.READY:
        return "completed"
    if doc.status == DocumentStatus.FAILED:
        return "failed"
    if doc.status == DocumentStatus.PROCESSING:
        return "processing"
    if doc.status == DocumentStatus.PENDING:
        return "queued"
    return "queued"


def document_to_response(doc: Document) -> DocumentResponse:
    return DocumentResponse(
        id=doc.id,
        filename=doc.filename,
        original_name=doc.original_name,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        processing_view=processing_view(doc),
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )
