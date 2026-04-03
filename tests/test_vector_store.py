"""Unit tests for VectorStoreService and EmbeddingService."""
import numpy as np
import pytest

from app.services.vector_store import VectorStoreService, ChunkMetadata
from app.schemas.documents import QueryMetadataFilter


@pytest.fixture
def vector_store(tmp_path, monkeypatch):
    monkeypatch.setenv("FAISS_INDEX_DIR", str(tmp_path / "faiss"))
    # Re-instantiate so it picks up the patched path
    from app.core.config import get_settings
    get_settings.cache_clear()
    svc = VectorStoreService()
    yield svc
    get_settings.cache_clear()


def make_embeddings(n: int, dim: int = 1536) -> np.ndarray:
    rng = np.random.default_rng(42)
    vecs = rng.standard_normal((n, dim)).astype(np.float32)
    # L2 normalise
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / norms


def make_metadata(doc_id: str, n: int) -> list[ChunkMetadata]:
    return [
        ChunkMetadata(
            document_id=doc_id,
            document_name=f"{doc_id}.pdf",
            chunk_index=i,
            content=f"Chunk {i} from {doc_id}",
        )
        for i in range(n)
    ]


# ── Add & search ───────────────────────────────────────────────────────────

def test_add_and_search_basic(vector_store: VectorStoreService):
    user_id = "user-1"
    embeddings = make_embeddings(10)
    metadata = make_metadata("doc-a", 10)

    vector_store.add_chunks(user_id, embeddings, metadata)

    query = make_embeddings(1)[0]
    results = vector_store.search(user_id, query, top_k=3)

    assert len(results) == 3
    for r in results:
        assert r.metadata.document_id == "doc-a"
        assert 0.0 <= r.score <= 1.1  # cosine can slightly exceed 1.0 due to float precision


def test_search_empty_index(vector_store: VectorStoreService):
    results = vector_store.search("empty-user", make_embeddings(1)[0], top_k=5)
    assert results == []


def test_search_with_document_filter(vector_store: VectorStoreService):
    user_id = "user-2"
    emb_a = make_embeddings(5)
    emb_b = make_embeddings(5)

    vector_store.add_chunks(user_id, emb_a, make_metadata("doc-a", 5))
    vector_store.add_chunks(user_id, emb_b, make_metadata("doc-b", 5))

    query = make_embeddings(1)[0]
    results = vector_store.search(user_id, query, top_k=10, document_ids=["doc-b"])

    assert all(r.metadata.document_id == "doc-b" for r in results)


def test_search_with_metadata_name_filter(vector_store: VectorStoreService):
    user_id = "user-meta-1"
    emb = make_embeddings(6)
    vector_store.add_chunks(user_id, emb[:3], make_metadata("invoice-2024", 3))
    vector_store.add_chunks(user_id, emb[3:], make_metadata("report-q1", 3))

    query = make_embeddings(1)[0]
    results = vector_store.search(
        user_id,
        query,
        top_k=5,
        metadata_filters=QueryMetadataFilter(document_name_contains="report"),
    )

    assert results
    assert all("report" in r.metadata.document_name for r in results)


def test_search_with_metadata_chunk_filter(vector_store: VectorStoreService):
    user_id = "user-meta-2"
    emb = make_embeddings(8)
    vector_store.add_chunks(user_id, emb, make_metadata("doc-score", 8))

    query = make_embeddings(1)[0]
    no_results = vector_store.search(
        user_id,
        query,
        top_k=5,
        metadata_filters=QueryMetadataFilter(chunk_index_min=100),
    )
    assert no_results == []


def test_delete_document(vector_store: VectorStoreService):
    user_id = "user-3"
    embeddings = make_embeddings(6)
    meta_a = make_metadata("doc-a", 3)
    meta_b = make_metadata("doc-b", 3)

    vector_store.add_chunks(user_id, embeddings[:3], meta_a)
    vector_store.add_chunks(user_id, embeddings[3:], meta_b)

    removed = vector_store.delete_document(user_id, "doc-a")
    assert removed == 3

    query = make_embeddings(1)[0]
    results = vector_store.search(user_id, query, top_k=10)
    assert all(r.metadata.document_id == "doc-b" for r in results)


def test_delete_nonexistent_document(vector_store: VectorStoreService):
    user_id = "user-4"
    embeddings = make_embeddings(3)
    vector_store.add_chunks(user_id, embeddings, make_metadata("doc-x", 3))

    removed = vector_store.delete_document(user_id, "nonexistent")
    assert removed == 0


def test_total_chunks_counter(vector_store: VectorStoreService):
    user_id = "user-5"
    embeddings = make_embeddings(7)
    vector_store.add_chunks(user_id, embeddings, make_metadata("doc-c", 7))

    idx = vector_store._get_index(user_id)
    assert idx.total_chunks == 7


def test_user_isolation(vector_store: VectorStoreService):
    """Different users must not see each other's chunks."""
    emb = make_embeddings(5)
    vector_store.add_chunks("alice", emb, make_metadata("alice-doc", 5))

    query = make_embeddings(1)[0]
    results = vector_store.search("bob", query, top_k=5)
    assert results == []
