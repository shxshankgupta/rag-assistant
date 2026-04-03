from datetime import datetime
from pydantic import BaseModel, Field
from app.models.document import DocumentStatus
from app.core.config import get_settings

settings = get_settings()


class DocumentResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    file_size: int
    mime_type: str
    status: DocumentStatus
    chunk_count: int
    celery_task_id: str | None = None
    celery_state: str | None = None
    processing_view: str | None = Field(
        default=None,
        description="Human-readable stage: queued | processing | completed | failed",
    )
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentResponse]


class QueryMetadataFilter(BaseModel):
    document_name_contains: str | None = Field(
        default=None,
        max_length=255,
        description="Case-insensitive substring filter on document name.",
    )
    min_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score threshold for results.",
    )
    chunk_index_min: int | None = Field(default=None, ge=0)
    chunk_index_max: int | None = Field(default=None, ge=0)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    document_ids: list[str] | None = Field(
        default=None,
        description="Limit search to specific documents. None = search all user docs.",
    )
    top_k: int = Field(default=settings.top_k_results, ge=1, le=20)
    filters: QueryMetadataFilter | None = Field(
        default=None,
        description="Optional metadata filters applied during retrieval.",
    )
    stream: bool = Field(default=True)


class SourceChunk(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    content: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    query: str
    model: str
