import json
from collections.abc import AsyncGenerator
from time import perf_counter

import httpx
import tiktoken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.core.logging import get_logger
from app.models.document import Document, DocumentStatus
from app.schemas.documents import QueryRequest, QueryResponse, SourceChunk
from app.services.cache_service import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store import SearchResult, VectorStoreService

settings = get_settings()
logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a precise knowledge assistant. Your job is to answer questions
using ONLY the context provided below. Follow these rules strictly:

1. Base your answer exclusively on the provided context.
2. If the context does not contain enough information, say so clearly — do NOT invent facts.
3. Cite the source document name when referencing specific information.
4. Be concise and structured. Use bullet points when listing multiple items.
5. If the question is ambiguous, answer the most likely interpretation.

Context:
{context}
"""

NO_CONTEXT_ANSWER = (
    "I could not find relevant information in the selected document(s) "
    "to answer that question."
)


class OllamaChatClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
    ):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.timeout = httpx.Timeout(timeout_seconds or settings.ollama_timeout_seconds)

    async def chat(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(f"{self.base_url}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

        content = data.get("response", "")
        logger.debug(
            "ollama_generate_complete",
            model=self.model,
            done=bool(data.get("done")),
            response_chars=len(content) if isinstance(content, str) else 0,
        )
        return content.strip() if isinstance(content, str) else ""

    async def stream_chat(
        self, prompt: str
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "options": {"temperature": 0.2},
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("ollama_stream_bad_json", line_preview=line[:200])
                        continue

                    content = chunk.get("response", "")

                    if content:
                        yield content

                    if chunk.get("done", False):
                        logger.debug(
                            "ollama_generate_stream_done",
                            model=self.model,
                            done=bool(chunk.get("done")),
                        )
                        break


class RAGService:
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
        self.chat_client = OllamaChatClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
        self.encoding = self._get_encoding()

    async def query(self, request: QueryRequest, user_id: str) -> QueryResponse:
        """Non-streaming RAG query."""
        query_start = perf_counter()

        cache_key = await self.cache_service.make_query_response_key(
            user_id=user_id,
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
            filters=request.filters.model_dump() if request.filters else None,
        )

        cached = await self.cache_service.get(cache_key)
        if cached:
            try:
                payload = json.loads(cached)
                logger.info(
                    "rag_query_cache_hit",
                    user_id=user_id,
                    query_latency_ms=round((perf_counter() - query_start) * 1000, 2),
                )
                return QueryResponse.model_validate(payload)
            except Exception:
                await self.cache_service.delete(cache_key)

        retrieve_start = perf_counter()
        sources, context = await self._retrieve(request, user_id)
        retrieval_latency_ms = round((perf_counter() - retrieve_start) * 1000, 2)

        if not sources:
            logger.info(
                "rag_query_no_context",
                user_id=user_id,
                query_len=len(request.query),
                retrieval_latency_ms=retrieval_latency_ms,
                query_latency_ms=round((perf_counter() - query_start) * 1000, 2),
            )
            response_payload = QueryResponse(
                answer=NO_CONTEXT_ANSWER,
                sources=[],
                query=request.query,
                model=self.chat_client.model,
            )
            await self.cache_service.set(
                cache_key,
                self.cache_service.dumps_json(response_payload.model_dump()),
                ttl_seconds=settings.cache_query_response_ttl_seconds,
            )
            return response_payload

        prompt = self._build_prompt(request.query, context)

        generation_start = perf_counter()
        answer = await self.chat_client.chat(prompt)
        generation_latency_ms = round((perf_counter() - generation_start) * 1000, 2)
        if not answer:
            answer = NO_CONTEXT_ANSWER

        logger.info(
            "rag_query_complete",
            user_id=user_id,
            query_len=len(request.query),
            sources=len(sources),
            retrieval_latency_ms=retrieval_latency_ms,
            generation_latency_ms=generation_latency_ms,
            query_latency_ms=round((perf_counter() - query_start) * 1000, 2),
            model=self.chat_client.model,
        )

        response_payload = QueryResponse(
            answer=answer,
            sources=sources,
            query=request.query,
            model=self.chat_client.model,
        )
        await self.cache_service.set(
            cache_key,
            self.cache_service.dumps_json(response_payload.model_dump()),
            ttl_seconds=settings.cache_query_response_ttl_seconds,
        )
        return response_payload

    async def query_stream(
        self, request: QueryRequest, user_id: str
    ) -> AsyncGenerator[str, None]:
        """
        Streaming RAG query. Yields Server-Sent Events (SSE) strings.
        """
        stream_start = perf_counter()

        try:
            retrieve_start = perf_counter()
            sources, context = await self._retrieve(request, user_id)
            retrieval_latency_ms = round(
                (perf_counter() - retrieve_start) * 1000, 2
            )

            sources_payload = [s.model_dump() for s in sources]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources_payload})}\n\n"

            if not sources:
                logger.info(
                    "rag_stream_no_context",
                    user_id=user_id,
                    query_len=len(request.query),
                    retrieval_latency_ms=retrieval_latency_ms,
                    query_latency_ms=round((perf_counter() - stream_start) * 1000, 2),
                )
                yield f"data: {json.dumps({'type': 'token', 'content': NO_CONTEXT_ANSWER})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                yield "data: [DONE]\n\n"
                return

            prompt = self._build_prompt(request.query, context)

            async for token in self.chat_client.stream_chat(prompt):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"

            logger.info(
                "rag_stream_complete",
                user_id=user_id,
                sources=len(sources),
                retrieval_latency_ms=retrieval_latency_ms,
                query_latency_ms=round((perf_counter() - stream_start) * 1000, 2),
                model=self.chat_client.model,
            )
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            yield "data: [DONE]\n\n"

        except Exception as exc:
            logger.error("stream_error", error=str(exc))
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"

    async def _retrieve(
        self, request: QueryRequest, user_id: str
    ) -> tuple[list[SourceChunk], str]:
        """Embed query, search FAISS, validate doc ownership, build context."""
        doc_ids = request.document_ids
        if doc_ids:
            await self._validate_document_ownership(doc_ids, user_id)

        query_embedding = await self.embedding_service.embed_query(request.query)

        results: list[SearchResult] = self.vector_store.search(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=request.top_k,
            document_ids=doc_ids,
            metadata_filters=request.filters,
        )

        if not results:
            logger.warning("no_results_found", user_id=user_id, query=request.query[:80])

        sources = [
            SourceChunk(
                document_id=r.metadata.document_id,
                document_name=r.metadata.document_name,
                chunk_index=r.metadata.chunk_index,
                content=r.metadata.content,
                score=round(r.score, 4),
            )
            for r in results
        ]

        context = self._build_context(results, request.query)
        return sources, context

    def _build_context(self, results: list[SearchResult], query: str) -> str:
        if not results:
            return "No relevant context found."

        parts: list[str] = []
        context_budget_tokens = self._context_budget_tokens(query)
        used_tokens = 0

        for r in results:
            snippet = (
                f"[Source: {r.metadata.document_name}, chunk {r.metadata.chunk_index}]\n"
                f"{r.metadata.content}"
            )
            snippet_tokens = self._count_tokens(snippet)

            if used_tokens + snippet_tokens > context_budget_tokens:
                break

            parts.append(snippet)
            used_tokens += snippet_tokens

        return "\n\n---\n\n".join(parts)

    def _build_prompt(self, query: str, context: str) -> str:
        system_prompt = SYSTEM_PROMPT.format(context=context).strip()
        return f"{system_prompt}\n\nQuestion:\n{query.strip()}\n"

    async def _validate_document_ownership(
        self, doc_ids: list[str], user_id: str
    ) -> None:
        result = await self.db.execute(
            select(Document).where(
                Document.id.in_(doc_ids),
                Document.owner_id == user_id,
                Document.status == DocumentStatus.READY,
            )
        )
        found = {doc.id for doc in result.scalars().all()}
        missing = set(doc_ids) - found

        if missing:
            raise ValidationError(
                f"Documents not found or not ready: {', '.join(sorted(missing))}"
            )

    def _get_encoding(self):
        return tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _context_budget_tokens(self, query: str) -> int:
        system_tokens = self._count_tokens(SYSTEM_PROMPT.format(context=""))
        query_tokens = self._count_tokens(query)
        completion_reserve = 1200

        budget = (
            settings.max_context_tokens
            - system_tokens
            - query_tokens
            - completion_reserve
        )
        return max(200, budget)
