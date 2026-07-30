import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "+998900000001",
        "password": "StrongPass1",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "duplicate@example.com",
        "phone": "+998900000002",
        "password": "StrongPass1",
    }
    await client.post("/api/v1/auth/register", json=payload)
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    register_payload = {
        "first_name": "Login",
        "last_name": "Test",
        "email": "login@example.com",
        "phone": "+998900000003",
        "password": "StrongPass1",
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "StrongPass1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    payload = {
        "first_name": "Wrong",
        "last_name": "Pass",
        "email": "wrong@example.com",
        "phone": "+998900000004",
        "password": "StrongPass1",
    }
    await client.post("/api/v1/auth/register", json=payload)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass1"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient):
    register_payload = {
        "first_name": "Refresh",
        "last_name": "Test",
        "email": "refresh@example.com",
        "phone": "+998900000005",
        "password": "StrongPass1",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=register_payload)
    refresh_token = reg_resp.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient):
    register_payload = {
        "first_name": "Me",
        "last_name": "Test",
        "email": "me@example.com",
        "phone": "+998900000006",
        "password": "StrongPass1",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=register_payload)
    access_token = reg_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["first_name"] == "Me"


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient):
    register_payload = {
        "first_name": "Change",
        "last_name": "Pass",
        "email": "changepass@example.com",
        "phone": "+998900000007",
        "password": "StrongPass1",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=register_payload)
    access_token = reg_resp.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "StrongPass1", "new_password": "NewStrong1"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"


@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    register_payload = {
        "first_name": "Logout",
        "last_name": "Test",
        "email": "logout@example.com",
        "phone": "+998900000008",
        "password": "StrongPass1",
    }
    reg_resp = await client.post("/api/v1/auth/register", json=register_payload)
    access_token = reg_resp.json()["access_token"]
    refresh_token = reg_resp.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
