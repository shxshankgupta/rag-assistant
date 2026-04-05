import asyncio
import uuid
from pathlib import Path

import aiofiles
from fastapi import UploadFile
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ValidationError, NotFoundError, ForbiddenError
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.schemas.documents import DocumentListResponse
from app.services.cache_service import CacheService
from app.services.document_response_builder import document_to_response
from app.services.document_processing import chunk_text, extract_pdf_text
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import ChunkMetadata, VectorStoreService

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
    # Upload & processing
    # ------------------------------------------------------------------ #

    async def upload_document(self, file: UploadFile, owner: User) -> Document:
        """Validate, save, extract, chunk, embed, and index a PDF in one request."""
        content, ext = await self._validate_file(file)
        file_path, filename = await self._save_file(content, ext, owner.id)
        file_size = len(content)

        doc = Document(
            owner_id=owner.id,
            filename=filename,
            original_name=file.filename or filename,
            file_path=str(file_path),
            file_size=file_size,
            mime_type=file.content_type or "application/pdf",
            status=DocumentStatus.PROCESSING,
        )
        self.db.add(doc)
        await self.db.flush()
        await self.db.refresh(doc)
        logger.info("document_saved", doc_id=doc.id, name=doc.original_name)

        try:
            chunk_count = await self._process_document(doc, owner.id)
        except Exception:
            self.vector_store.delete_document(owner.id, doc.id)
            try:
                Path(doc.file_path).unlink(missing_ok=True)
            except OSError as exc:
                logger.warning("file_delete_failed", path=doc.file_path, error=str(exc))
            raise

        doc.status = DocumentStatus.READY
        doc.chunk_count = chunk_count
        doc.error_message = None
        await self.db.flush()
        await self.cache_service.bump_user_corpus_version(owner.id)

        doc_count = await self._count_user_documents(owner.id)
        logger.info(
            "document_processed",
            doc_id=doc.id,
            chunks=chunk_count,
            user_id=owner.id,
            document_count=doc_count,
        )
        return doc

    async def upload_and_process(self, file: UploadFile, owner: User) -> Document:
        """Backward-compatible helper used by tests and older callers."""
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
            items=[document_to_response(d) for d in docs],
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

    async def _validate_file(self, file: UploadFile) -> tuple[bytes, str]:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValidationError("Unsupported file type. Only PDF files are accepted.")

        content = await file.read()
        await file.seek(0)
        if len(content) > settings.max_upload_size_bytes:
            raise ValidationError(
                f"File too large. Maximum size is {settings.max_upload_size_mb} MB."
            )
        if not content:
            raise ValidationError("Uploaded file is empty.")
        if not content.lstrip().startswith(b"%PDF"):
            raise ValidationError("Uploaded file is not a valid PDF.")
        return content, ext

    async def _save_file(
        self, content: bytes, ext: str, owner_id: str
    ) -> tuple[Path, str]:
        filename = f"{uuid.uuid4().hex}{ext}"
        owner_dir = Path(settings.upload_dir) / owner_id
        owner_dir.mkdir(parents=True, exist_ok=True)
        file_path = owner_dir / filename

        async with aiofiles.open(file_path, "wb") as f:
            await f.write(content)

        return file_path, filename

    async def _process_document(self, doc: Document, user_id: str) -> int:
        text = await asyncio.to_thread(extract_pdf_text, doc.file_path)
        chunks = chunk_text(
            text,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )
        if not chunks:
            raise ValidationError("No text chunks could be created from this PDF.")

        embeddings = await self.embedding_service.embed_texts(chunks)
        metadatas = [
            ChunkMetadata(
                document_id=doc.id,
                document_name=doc.original_name,
                chunk_index=index,
                content=chunk,
            )
            for index, chunk in enumerate(chunks)
        ]
        self.vector_store.add_chunks(user_id, embeddings, metadatas)
        return len(chunks)

    async def _count_user_documents(self, owner_id: str) -> int:
        result = await self.db.execute(
            select(func.count()).select_from(Document).where(Document.owner_id == owner_id)
        )
        return int(result.scalar_one() or 0)
