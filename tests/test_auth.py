"""Integration tests for auth routes."""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Str0ngP@ss!",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "email": "dup@example.com",
        "username": "user1",
        "password": "Str0ngP@ss!",
    }
    await client.post("/api/v1/auth/register", json=payload)
    resp = await client.post(
        "/api/v1/auth/register",
        json={**payload, "username": "user2"},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "username": "loginuser", "password": "Str0ngP@ss!"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "loginuser", "password": "Str0ngP@ss!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wp@example.com", "username": "wpuser", "password": "Str0ngP@ss!"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "wpuser", "password": "WrongPassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "me@example.com", "username": "meuser", "password": "Str0ngP@ss!"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "meuser", "password": "Str0ngP@ss!"},
    )
    token = login.json()["access_token"]
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401
