from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    # App
    app_name: str = "RAG Knowledge Assistant"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Security
    secret_key: str = Field(default="dev-secret-key-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # OpenAI (optional now)
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"

    # Local embeddings
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dimension: int = 384

    # Ollama
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5:3b"
    ollama_timeout_seconds: float = 180.0

    # Database / cache / queue
    database_url: str = f"sqlite+aiosqlite:///{(DATA_DIR / 'app.db').as_posix()}"
    redis_url: str = "redis://localhost:6379/0"
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"

    # Files / vector store
    upload_dir: str = str(DATA_DIR / "uploads")
    faiss_index_dir: str = str(DATA_DIR / "faiss_index")
    max_file_size_mb: int = 20

    # Raw env values (safe parsing)
    allowed_file_extensions_raw: str = Field(default="pdf", alias="ALLOWED_FILE_EXTENSIONS")
    allowed_origins_raw: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="ALLOWED_ORIGINS",
    )

    # Retrieval
    chunk_size: int = 1000
    chunk_overlap: int = 150
    top_k_results: int = 5
    max_context_tokens: int = 8000

    # Rate limits
    rate_limit_requests: int = 60
    rate_limit_window_seconds: int = 60
    api_rate_limit_per_minute: int = 60
    query_rate_limit_per_minute: int = 30
    auth_rate_limit_per_minute: int = 20

    # Cache
    cache_default_ttl_seconds: int = 300
    cache_query_response_ttl_seconds: int = 300
    cache_embedding_ttl_seconds: int = 300
    cache_corpus_version_ttl_seconds: int = 86400
    cache_memory_max_items: int = 1000

    # Frontend
    frontend_url: str = "http://localhost:3000"

    @property
    def allowed_file_extensions(self) -> list[str]:
        raw = (self.allowed_file_extensions_raw or "").strip()
        if not raw:
            return ["pdf"]
        return [ext.strip().lower() for ext in raw.split(",") if ext.strip()]

    @property
    def allowed_origins(self) -> list[str]:
        raw = (self.allowed_origins_raw or "").strip()
        if not raw:
            return ["http://localhost:3000", "http://127.0.0.1:3000"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def origins_list(self) -> list[str]:
        return self.allowed_origins

    @property
    def celery_broker_url(self) -> str:
        return self.broker_url

    @property
    def celery_result_backend(self) -> str:
        return self.result_backend

    @property
    def retrieval_top_k(self) -> int:
        return self.top_k_results

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_upload_size_mb(self) -> int:
        return self.max_file_size_mb

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_file_size_bytes


@lru_cache
def get_settings() -> Settings:
    return Settings()
