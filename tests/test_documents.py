"""Integration tests for document upload and management routes."""
import io
import pytest
from unittest.mock import MagicMock, patch
from httpx import AsyncClient

from tests.conftest import register_and_login, auth_headers


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    pdf_bytes = b"%PDF-1.4 fake"
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_non_pdf_rejected(client: AsyncClient):
    tokens = await register_and_login(client, "doc1")
    resp = await client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        headers=auth_headers(tokens),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_documents_empty(client: AsyncClient):
    tokens = await register_and_login(client, "doc2")
    resp = await client.get(
        "/api/v1/documents/",
        headers=auth_headers(tokens),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_get_nonexistent_document(client: AsyncClient):
    tokens = await register_and_login(client, "doc3")
    resp = await client.get(
        "/api/v1/documents/nonexistent-id",
        headers=auth_headers(tokens),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_pdf_accepted(client: AsyncClient):
    """Upload a minimal valid PDF and verify the 202 response."""
    tokens = await register_and_login(client, "doc4")

    # Minimal valid PDF bytes
    minimal_pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"trailer\n<< /Root 1 0 R /Size 4 >>\nstartxref\n9\n%%EOF"
    )

    with patch(
        "app.workers.tasks.process_document_embedding.delay",
        return_value=MagicMock(id="test-task-id"),
    ):
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("sample.pdf", io.BytesIO(minimal_pdf), "application/pdf")},
            headers=auth_headers(tokens),
        )

    assert resp.status_code == 202
    data = resp.json()
    assert data["original_name"] == "sample.pdf"
    assert data["status"] in ("pending", "processing")
    assert "id" in data


@pytest.mark.asyncio
async def test_delete_document_not_owned(client: AsyncClient):
    """User B cannot delete User A's document."""
    tokens_a = await register_and_login(client, "docA")
    tokens_b = await register_and_login(client, "docB")

    minimal_pdf = b"%PDF-1.4\n%%EOF"

    with patch(
        "app.workers.tasks.process_document_embedding.delay",
        return_value=MagicMock(id="test-task-id"),
    ):
        upload = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("a.pdf", io.BytesIO(minimal_pdf), "application/pdf")},
            headers=auth_headers(tokens_a),
        )

    doc_id = upload.json()["id"]

    resp = await client.delete(
        f"/api/v1/documents/{doc_id}",
        headers=auth_headers(tokens_b),
    )
    assert resp.status_code in (403, 404)
