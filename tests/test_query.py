"""Integration tests for RAG query routes."""
import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

from tests.conftest import register_and_login, auth_headers


def _mock_rag_service():
    """Return a RAGService mock with sensible defaults."""
    from app.schemas.documents import QueryResponse, SourceChunk

    mock = MagicMock()
    mock.query = AsyncMock(
        return_value=QueryResponse(
            answer="The capital of France is Paris.",
            sources=[
                SourceChunk(
                    document_id="doc-1",
                    document_name="geography.pdf",
                    chunk_index=0,
                    content="France is a country in Western Europe. Its capital is Paris.",
                    score=0.95,
                )
            ],
            query="What is the capital of France?",
            model="gpt-4o-mini",
        )
    )
    return mock


@pytest.mark.asyncio
async def test_query_requires_auth(client: AsyncClient):
    resp = await client.post(
        "/api/v1/query/",
        json={"query": "hello", "stream": False},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_query_empty_string_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "q1")
    resp = await client.post(
        "/api/v1/query/",
        json={"query": "", "stream": False},
        headers=auth_headers(tokens),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_non_streaming(client: AsyncClient):
    tokens = await register_and_login(client, "q2")

    mock_svc = _mock_rag_service()

    with patch("app.api.routes.query.get_rag_service", return_value=lambda: mock_svc):
        from app.api.deps import get_rag_service
        from app.main import app

        app.dependency_overrides[get_rag_service] = lambda: mock_svc

        resp = await client.post(
            "/api/v1/query/",
            json={"query": "What is the capital of France?", "stream": False},
            headers=auth_headers(tokens),
        )

        app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert "sources" in data
    assert isinstance(data["sources"], list)


@pytest.mark.asyncio
async def test_query_top_k_validation(client: AsyncClient):
    """top_k must be between 1 and 20."""
    tokens = await register_and_login(client, "q3")
    resp = await client.post(
        "/api/v1/query/",
        json={"query": "hello", "top_k": 100, "stream": False},
        headers=auth_headers(tokens),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_query_stream_endpoint_exists(client: AsyncClient):
    """Streaming endpoint should return 401 without auth, not 404."""
    resp = await client.post(
        "/api/v1/query/stream",
        json={"query": "test", "stream": True},
    )
    assert resp.status_code == 401
