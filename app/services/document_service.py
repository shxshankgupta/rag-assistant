import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import get_settings
from app.core.exceptions import ValidationError, NotFoundError, ForbiddenError
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.documents import DocumentListResponse
from app.services.cache_service import CacheService
from app.services.document_response_builder import document_to_response
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService

settings = get_settings()
logger = get_logger(__name__)

ALLOWED_MIME_TYPES = {"application/pdf"}
ALLOWED_EXTENSIONS = {".pdf"}


class DocumentService:
    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        vector_store: VectorStoreService,
        cache_service: CacheService,
    ):
        self.db = db
        self.embedding_service = embedding_service
        self.vector_store = vector_store
        self.cache_service = cache_service
        Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Upload & Celery
    # ------------------------------------------------------------------ #

    async def upload_document(self, file: UploadFile, owner: User) -> Document:
        """Validate/save PDF and persist as pending; embedding runs in Celery."""
        await self._validate_file(file)

        file_path, filename, file_size = await self._save_file(file, owner.id)

        doc = Document(
            owner_id=owner.id,
            filename=filename,
            original_name=file.filename or filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=file.content_type or "application/pdf",
            status=DocumentStatus.PENDING,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        logger.info("document_saved", doc_id=doc.id, name=doc.original_name)
        doc_count = await self._count_user_documents(owner.id)
        logger.info("user_document_count", user_id=owner.id, document_count=doc_count)

        return doc

    async def enqueue_embedding_task(self, doc: Document, user_id: str) -> None:
        """Dispatch Celery task; stores task id on the document row."""
        from app.workers.tasks import process_document_embedding

        async_result = process_document_embedding.delay(doc.id, user_id)
        doc.celery_task_id = async_result.id
        await self.db.flush()

    async def upload_and_process(self, file: UploadFile, owner: User) -> Document:
        """Backward-compatible helper for callers that only create the row."""
        return await self.upload_document(file, owner)

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    async def list_documents(self, owner_id: str) -> DocumentListResponse:
        result = await self.db.execute(
            select(Document)
            .where(Document.owner_id == owner_id)
            .order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        logger.info("user_document_count", user_id=owner_id, document_count=len(docs))
        return DocumentListResponse(
            total=len(docs),
            items=[document_to_response(d, include_celery_state=False) for d in docs],
        )

    async def get_document(self, doc_id: str, owner_id: str) -> Document:
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            raise NotFoundError("Document", doc_id)
        if doc.owner_id != owner_id:
            raise ForbiddenError("You do not own this document")
        return doc

    async def delete_document(self, doc_id: str, owner_id: str) -> None:
        doc = await self.get_document(doc_id, owner_id)

        self.vector_store.delete_document(owner_id, doc_id)
        await self.cache_service.bump_user_corpus_version(owner_id)

        try:
            Path(doc.file_path).unlink(missing_ok=True)
        except OSError as e:
            logger.warning("file_delete_failed", path=doc.file_path, error=str(e))

        await self.db.delete(doc)
        await self.db.flush()
        doc_count = await self._count_user_documents(owner_id)
        logger.info("user_document_count", user_id=owner_id, document_count=doc_count)
        logger.info("document_deleted", doc_id=doc_id, owner_id=owner_id)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    async def _validate_file(self, file: UploadFile) -> None:
        if file.content_type not in ALLOWED_MIME_TYPES:
            raise ValidationError(
                f"Unsupported file type: {file.content_type}. Only PDF is accepted."
            )
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError(f"Unsupported extension: {ext}")

        content = await file.read()
        await file.seek(0)
        if len(content) > settings.max_upload_size_bytes:
            raise ValidationError(
                f"File too large. Maximum size is {settings.max_upload_size_mb} MB."
            )

    async def _save_file(
        self, file: UploadFile, owner_id: str
    ) -> tuple[Path, str, int]:
        content = await file.read()
        await file.seek(0)

        ext = Path(file.filename or "file").suffix.lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        owner_dir = Path(settings.upload_dir) / owner_id
        owner_dir.mkdir(parents=True, exist_ok=True)
        file_path = owner_dir / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return file_path, filename, len(content)

    async def _count_user_documents(self, owner_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Document).where(Document.owner_id == owner_id)
        )
        return int(result.scalar_one() or 0)
