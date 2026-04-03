import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import faiss
import numpy as np

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.documents import QueryMetadataFilter

settings = get_settings()
logger = get_logger(__name__)


def _normalize_l2(arr: np.ndarray) -> None:
    faiss.normalize_L2(arr)  # type: ignore[call-arg]


def _read_index(path: Path) -> faiss.Index:
    return cast(faiss.Index, faiss.read_index(str(path)))  # type: ignore[call-arg]


def _write_index(index: faiss.Index, path: Path) -> None:
    faiss.write_index(index, str(path))  # type: ignore[call-arg]


def _index_search(
    index: faiss.Index, query: np.ndarray, top_k: int
) -> tuple[np.ndarray, np.ndarray]:
    scores, indices = index.search(query, top_k)  # type: ignore[call-arg]
    return cast(tuple[np.ndarray, np.ndarray], (scores, indices))


def _index_add(index: faiss.Index, vectors: np.ndarray) -> None:
    index.add(vectors)  # type: ignore[call-arg]


def _index_reconstruct_all(index: faiss.Index, dimension: int) -> np.ndarray:
    total = int(index.ntotal)
    vectors = np.zeros((total, dimension), dtype=np.float32)
    if total > 0:
        index.reconstruct_n(0, total, vectors)  # type: ignore[call-arg]
    return vectors


@dataclass
class ChunkMetadata:
    document_id: str
    document_name: str
    chunk_index: int
    content: str


@dataclass
class SearchResult:
    metadata: ChunkMetadata
    score: float


class UserVectorIndex:
    """FAISS index for a single user, with persistent metadata store."""

    def __init__(self, user_id: str, dimension: int):
        self.user_id = user_id
        self.dimension = dimension

        self._index_dir = Path(settings.faiss_index_dir) / user_id
        self._index_dir.mkdir(parents=True, exist_ok=True)

        self._index_path = self._index_dir / "index.faiss"
        self._meta_path = self._index_dir / "metadata.json"
        self._lock = threading.RLock()

        self._index: faiss.Index | None = None
        self._metadata: list[dict[str, Any]] = []

        self._index_mtime: float | None = None
        self._meta_mtime: float | None = None

        self._reload_from_disk(force=True)

    def _current_mtime(self, path: Path) -> float | None:
        if not path.exists():
            return None
        return path.stat().st_mtime

    def _create_empty_index(self) -> faiss.Index:
        return faiss.IndexFlatIP(self.dimension)

    def _load_index_from_disk(self) -> faiss.Index:
        if self._index_path.exists():
            index = _read_index(self._index_path)
            logger.debug("faiss_index_loaded", user_id=self.user_id, ntotal=index.ntotal)
            return index
        return self._create_empty_index()

    def _load_metadata_from_disk(self) -> list[dict[str, Any]]:
        if self._meta_path.exists():
            with open(self._meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        return []

    def _reload_from_disk(self, force: bool = False) -> None:
        with self._lock:
            index_mtime = self._current_mtime(self._index_path)
            meta_mtime = self._current_mtime(self._meta_path)

            needs_reload = force or (
                index_mtime != self._index_mtime or meta_mtime != self._meta_mtime
            )

            if not needs_reload:
                return

            self._index = self._load_index_from_disk()
            self._metadata = self._load_metadata_from_disk()
            self._index_mtime = index_mtime
            self._meta_mtime = meta_mtime

            ntotal = int(self._index.ntotal)
            if ntotal != len(self._metadata):
                logger.warning(
                    "faiss_metadata_mismatch",
                    user_id=self.user_id,
                    index_total=ntotal,
                    metadata_total=len(self._metadata),
                )

    def _save(self) -> None:
        if self._index is None:
            self._index = self._create_empty_index()

        _write_index(self._index, self._index_path)
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(self._metadata, f, ensure_ascii=False)

        self._index_mtime = self._current_mtime(self._index_path)
        self._meta_mtime = self._current_mtime(self._meta_path)

    def _prepare_embeddings(self, embeddings: np.ndarray) -> np.ndarray:
        arr = np.asarray(embeddings, dtype=np.float32)

        if arr.ndim != 2:
            raise ValueError(
                f"Embeddings must be 2D. Got shape={getattr(arr, 'shape', None)}"
            )

        if arr.shape[1] != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch. Expected {self.dimension}, got {arr.shape[1]}"
            )

        arr = np.ascontiguousarray(arr)
        _normalize_l2(arr)
        return arr

    def _prepare_query(self, query_embedding: np.ndarray) -> np.ndarray:
        query = np.asarray(query_embedding, dtype=np.float32)

        if query.ndim == 1:
            query = query.reshape(1, -1)

        if query.ndim != 2:
            raise ValueError(
                f"Query embedding must be 1D or 2D. Got shape={getattr(query, 'shape', None)}"
            )

        if query.shape[1] != self.dimension:
            raise ValueError(
                f"Query embedding dimension mismatch. Expected {self.dimension}, got {query.shape[1]}"
            )

        query = np.ascontiguousarray(query)
        _normalize_l2(query)
        return query

    def add_chunks(
        self, embeddings: np.ndarray, metadatas: list[ChunkMetadata]
    ) -> None:
        if len(metadatas) == 0:
            logger.warning("add_chunks_called_with_no_metadata", user_id=self.user_id)
            return

        vectors = self._prepare_embeddings(embeddings)

        if len(vectors) != len(metadatas):
            raise ValueError(
                f"Embeddings count ({len(vectors)}) does not match metadata count ({len(metadatas)})"
            )

        with self._lock:
            self._reload_from_disk()

            if self._index is None:
                self._index = self._create_empty_index()

            _index_add(self._index, vectors)
            self._metadata.extend(
                {
                    "document_id": m.document_id,
                    "document_name": m.document_name,
                    "chunk_index": m.chunk_index,
                    "content": m.content,
                }
                for m in metadatas
            )

            self._save()

            logger.info(
                "chunks_added",
                user_id=self.user_id,
                count=len(metadatas),
                total=self._index.ntotal,
            )

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        metadata_filters: QueryMetadataFilter | None = None,
    ) -> list[SearchResult]:
        with self._lock:
            self._reload_from_disk()

            if self._index is None or self._index.ntotal == 0:
                return []

            query = self._prepare_query(query_embedding)

            has_filters = bool(document_ids or metadata_filters)
            fetch_multiplier = 25 if has_filters else 1
            fetch_k = min(max(top_k * fetch_multiplier, top_k), int(self._index.ntotal))

            scores, indices = _index_search(self._index, query, fetch_k)

            results: list[SearchResult] = []
            for score, idx in zip(scores[0], indices[0]):
                if idx == -1:
                    continue
                if idx >= len(self._metadata):
                    logger.warning(
                        "faiss_result_index_out_of_range",
                        user_id=self.user_id,
                        idx=int(idx),
                        metadata_total=len(self._metadata),
                    )
                    continue

                meta = self._metadata[idx]

                if document_ids and meta["document_id"] not in document_ids:
                    continue

                if metadata_filters:
                    doc_name_filter = metadata_filters.document_name_contains
                    if (
                        doc_name_filter
                        and doc_name_filter.lower()
                        not in meta["document_name"].lower()
                    ):
                        continue

                    if (
                        metadata_filters.chunk_index_min is not None
                        and meta["chunk_index"] < metadata_filters.chunk_index_min
                    ):
                        continue

                    if (
                        metadata_filters.chunk_index_max is not None
                        and meta["chunk_index"] > metadata_filters.chunk_index_max
                    ):
                        continue

                    if (
                        metadata_filters.min_score is not None
                        and float(score) < metadata_filters.min_score
                    ):
                        continue

                results.append(
                    SearchResult(
                        metadata=ChunkMetadata(**meta),
                        score=float(score),
                    )
                )

                if len(results) >= top_k:
                    break

            logger.debug(
                "faiss_search_complete",
                user_id=self.user_id,
                requested_top_k=top_k,
                returned=len(results),
                index_total=int(self._index.ntotal),
            )

            return results

    def delete_document(self, document_id: str) -> int:
        """Remove all chunks for a document. Returns count removed."""
        with self._lock:
            self._reload_from_disk()

            if self._index is None:
                self._index = self._create_empty_index()

            keep_indices = [
                i for i, m in enumerate(self._metadata) if m["document_id"] != document_id
            ]
            removed = len(self._metadata) - len(keep_indices)

            if removed == 0:
                return 0

            new_index = self._create_empty_index()

            if keep_indices and self._index.ntotal > 0:
                all_vectors = _index_reconstruct_all(self._index, self.dimension)
                kept_vectors = np.ascontiguousarray(
                    all_vectors[keep_indices], dtype=np.float32
                )
                if len(kept_vectors) > 0:
                    _normalize_l2(kept_vectors)
                    _index_add(new_index, kept_vectors)

            self._index = new_index
            self._metadata = [self._metadata[i] for i in keep_indices]
            self._save()

            logger.info(
                "document_deleted_from_index",
                user_id=self.user_id,
                document_id=document_id,
                removed=removed,
            )
            return removed

    @property
    def total_chunks(self) -> int:
        with self._lock:
            self._reload_from_disk()
            if self._index is None:
                return 0
            return int(self._index.ntotal)


class VectorStoreService:
    """Manages per-user FAISS indices."""

    def __init__(self):
        self._indices: dict[str, UserVectorIndex] = {}
        self._lock = threading.Lock()
        self.dimension = settings.embedding_dimension
        Path(settings.faiss_index_dir).mkdir(parents=True, exist_ok=True)

    def _get_index(self, user_id: str) -> UserVectorIndex:
        with self._lock:
            if user_id not in self._indices:
                self._indices[user_id] = UserVectorIndex(user_id, self.dimension)
            return self._indices[user_id]

    def add_chunks(
        self,
        user_id: str,
        embeddings: np.ndarray,
        metadatas: list[ChunkMetadata],
    ) -> None:
        self._get_index(user_id).add_chunks(embeddings, metadatas)

    def search(
        self,
        user_id: str,
        query_embedding: np.ndarray,
        top_k: int = 5,
        document_ids: list[str] | None = None,
        metadata_filters: QueryMetadataFilter | None = None,
    ) -> list[SearchResult]:
        return self._get_index(user_id).search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_ids=document_ids,
            metadata_filters=metadata_filters,
        )

    def delete_document(self, user_id: str, document_id: str) -> int:
        return self._get_index(user_id).delete_document(document_id)
