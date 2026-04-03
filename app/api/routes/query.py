from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, enforce_query_rate_limit, get_rag_service
from app.schemas.documents import QueryRequest, QueryResponse
from app.services.rag_service import RAGService

router = APIRouter(prefix="/query", tags=["RAG Query"])


@router.post("/", response_model=QueryResponse, dependencies=[Depends(enforce_query_rate_limit)])
async def query(
    request: QueryRequest,
    current_user: CurrentUser,
    rag_svc: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    """
    Non-streaming RAG query. Returns the complete answer once done.
    Set `stream: false` in the request body.
    """
    request.stream = False
    return await rag_svc.query(request, current_user.id)


@router.post("/stream", dependencies=[Depends(enforce_query_rate_limit)])
async def query_stream(
    request: QueryRequest,
    current_user: CurrentUser,
    rag_svc: RAGService = Depends(get_rag_service),
) -> StreamingResponse:
    """
    Streaming RAG query using Server-Sent Events (SSE).

    Events emitted:
    - `{"type": "sources", "sources": [...]}` — retrieved context chunks
    - `{"type": "token", "content": "..."}` — LLM tokens as they arrive
    - `{"type": "done"}` — stream finished
    - `{"type": "error", "message": "..."}` — on failure
    - `[DONE]` — SSE stream terminator

    **Client example (JavaScript):**
    ```js
    const es = new EventSource('/api/v1/query/stream');
    // Use fetch + ReadableStream for POST with body
    ```
    """
    request.stream = True
    return StreamingResponse(
        rag_svc.query_stream(request, current_user.id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )
