
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database.database import get_async_db
import random
import string

# Test user credentials
RANDOM_SUFFIX = "".join(random.choices(string.digits, k=8))
TEST_USER = {
    "number": f"7{RANDOM_SUFFIX}",
    "country_code": "+254",
    "password": "testpassword123"
}

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest.fixture(scope="module")
async def auth_token(client):
    # 1. Test Registration
    reg_response = await client.post("/auth/register", json=TEST_USER)
    assert reg_response.status_code in [201, 400]
    
    # 2. Test Login
    login_data = {
        "username": f"{TEST_USER['country_code']}{TEST_USER['number']}",
        "password": TEST_USER["password"]
    }
    login_response = await client.post("/auth/login", data=login_data)
    assert login_response.status_code == 200
    token_data = login_response.json()
    return token_data["access_token"]

@pytest.mark.anyio
async def test_database_connection():
    async for session in get_async_db():
        assert session is not None
        from sqlalchemy import text
        result = await session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        break

@pytest.mark.anyio
async def test_registration_and_login(auth_token):
    assert auth_token is not None

@pytest.mark.anyio
async def test_get_profile(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["number"] == f"{TEST_USER['country_code']}{TEST_USER['number']}"

@pytest.mark.anyio
async def test_get_countdown(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await client.get("/countdown/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "task_reset_seconds" in data

@pytest.mark.anyio
async def test_unauthorized_access(client):
    response = await client.get("/auth/me")
    assert response.status_code == 401

if __name__ == "__main__":
    import sys
    pytest.main([__file__])
