"""Async document extraction → chunk → embed → index (runs inside Celery via asyncio.run)."""

import asyncio

from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader
from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentStatus
from app.services.cache_service import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import VectorStoreService, ChunkMetadata

settings = get_settings()
logger = get_logger(__name__)


class NonRetryableProcessingError(Exception):
    """Validation/content errors that should not trigger Celery retries."""

    pass


def _splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )


def _extract_pdf_text(file_path: str) -> str:
    reader = PdfReader(file_path)
    pages: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        pages.append(page_text)
    return "\n\n".join(pages)


async def run_document_embedding_pipeline(doc_id: str, user_id: str) -> None:
    """Full pipeline: load doc, extract, chunk, embed, index, update status."""
    embedding_service = EmbeddingService(CacheService())
    vector_store = VectorStoreService()
    cache_service = CacheService()
    splitter = _splitter()

    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if not doc:
                return

            doc.status = DocumentStatus.PROCESSING
            await session.commit()

            text = await asyncio.to_thread(_extract_pdf_text, doc.file_path)
            if not text.strip():
                raise NonRetryableProcessingError("PDF contains no extractable text")

            chunks = splitter.split_text(text)
            if not chunks:
                raise NonRetryableProcessingError("No chunks produced from document")

            embeddings = await embedding_service.embed_texts(chunks)

            metadatas = [
                ChunkMetadata(
                    document_id=doc.id,
                    document_name=doc.original_name,
                    chunk_index=i,
                    content=chunk,
                )
                for i, chunk in enumerate(chunks)
            ]
            vector_store.add_chunks(user_id, embeddings, metadatas)

            doc.status = DocumentStatus.READY
            doc.chunk_count = len(chunks)
            doc.error_message = None
            await session.commit()
            await cache_service.bump_user_corpus_version(user_id)

            logger.info(
                "document_processed",
                doc_id=doc.id,
                chunks=len(chunks),
            )
        except NonRetryableProcessingError as exc:
            await session.rollback()
            logger.warning("document_processing_non_retryable", doc_id=doc_id, error=str(exc))
            await _mark_failed(doc_id, str(exc))
            raise
        except Exception as exc:
            await session.rollback()
            logger.error("document_processing_failed", doc_id=doc_id, error=str(exc))
            raise


async def _mark_failed(doc_id: str, message: str) -> None:
    async with AsyncSessionLocal() as session:
        try:
            result = await session.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error_message = message[:500]
                await session.commit()
        except Exception:
            await session.rollback()
