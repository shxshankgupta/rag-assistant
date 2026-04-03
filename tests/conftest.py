"""
Shared test fixtures.
Uses an in-memory SQLite database so tests are isolated and fast.
"""
import os
import pytest
import pytest_asyncio

# Point to test env BEFORE importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-chars-xxxxxxxx")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("UPLOAD_DIR", "/tmp/rag_test_uploads")
os.environ.setdefault("FAISS_INDEX_DIR", "/tmp/rag_test_faiss")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.db.session import Base, get_db
from app.main import app
from app.core.config import get_settings

settings = get_settings()

# ── In-memory test engine ──────────────────────────────────────────────────
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP client with the test DB injected."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c

    app.dependency_overrides.clear()


# ── Convenience helpers ────────────────────────────────────────────────────

async def register_and_login(client: AsyncClient, suffix: str = "") -> dict:
    """Register a user and return the token response dict."""
    username = f"user{suffix}"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{username}@example.com",
            "username": username,
            "password": "Str0ngP@ss!",
        },
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Str0ngP@ss!"},
    )
    return resp.json()


def auth_headers(token_response: dict) -> dict:
    return {"Authorization": f"Bearer {token_response['access_token']}"}
