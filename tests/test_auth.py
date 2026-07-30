import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login(client: AsyncClient, admin_token: str):
    create_payload = {
        "first_name": "Login",
        "last_name": "Test",
        "email": "logintest@example.com",
        "phone": "+998900000001",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create_resp.status_code == 201
    user = create_resp.json()

    login_payload = {
        "phone": user["phone"],
        "password": user["temporary_password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_token: str):
    login_payload = {
        "phone": "+998900000001",
        "password": "WrongPass1",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_wrong_phone(client: AsyncClient):
    payload = {
        "phone": "+999999999999",
        "password": "StrongPass1",
    }
    response = await client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, admin_token: str):
    create_payload = {
        "first_name": "Refresh",
        "last_name": "Test",
        "email": "refreshtest@example.com",
        "phone": "+998900000002",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user = create_resp.json()

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"phone": user["phone"], "password": user["temporary_password"]},
    )
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_register_endpoint_not_found(client: AsyncClient):
    payload = {
        "first_name": "Test",
        "last_name": "User",
        "email": "test@example.com",
        "phone": "+998900000003",
        "password": "StrongPass1",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "email" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "StrongPass1", "new_password": "654321"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully"


@pytest.mark.asyncio
async def test_change_password_wrong_current(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "WrongPass1", "new_password": "654321"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, admin_token: str):
    create_payload = {
        "first_name": "Logout",
        "last_name": "Test",
        "email": "logouttest@example.com",
        "phone": "+998900000004",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=create_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    user = create_resp.json()

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"phone": user["phone"], "password": user["temporary_password"]},
    )
    access_token = login_resp.json()["access_token"]
    refresh_token = login_resp.json()["refresh_token"]

    response = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
