import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_users_as_admin(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "pages" in data


@pytest.mark.asyncio
async def test_list_users_as_manager(client: AsyncClient, manager_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    payload = {
        "first_name": "New",
        "last_name": "User",
        "email": "newuser@example.com",
        "phone": "+998900000010",
        "role": "manager",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "manager"
    assert "temporary_password" in data
    assert len(data["temporary_password"]) == 6


@pytest.mark.asyncio
async def test_create_user_as_admin_no_password_in_request(client: AsyncClient, admin_token: str):
    payload = {
        "first_name": "NoPass",
        "last_name": "User",
        "email": "nopass@example.com",
        "phone": "+998900000020",
        "role": "client",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "temporary_password" in data


@pytest.mark.asyncio
async def test_create_user_as_manager_fails(client: AsyncClient, manager_token: str):
    payload = {
        "first_name": "Should",
        "last_name": "Fail",
        "email": "shouldfail@example.com",
        "phone": "+998900000030",
        "role": "client",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_list_users(client: AsyncClient, client_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_activate_deactivate_user(client: AsyncClient, admin_token: str):
    target_payload = {
        "first_name": "Target",
        "last_name": "User",
        "email": "target@example.com",
        "phone": "+998900000011",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=target_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    target_id = create_resp.json()["id"]

    deactivate_resp = await client.post(
        f"/api/v1/users/{target_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert deactivate_resp.status_code == 200
    assert deactivate_resp.json()["is_active"] is False

    activate_resp = await client.post(
        f"/api/v1/users/{target_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert activate_resp.status_code == 200
    assert activate_resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_delete_user(client: AsyncClient, admin_token: str):
    target_payload = {
        "first_name": "Delete",
        "last_name": "Me",
        "email": "deleteme@example.com",
        "phone": "+998900000012",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=target_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    target_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/users/{target_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "User deleted successfully"


@pytest.mark.asyncio
async def test_change_role(client: AsyncClient, admin_token: str):
    target_payload = {
        "first_name": "Role",
        "last_name": "Change",
        "email": "rolechange@example.com",
        "phone": "+998900000013",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=target_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    target_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/users/{target_id}/role",
        json={"role": "manager"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"


@pytest.mark.asyncio
async def test_reset_password(client: AsyncClient, admin_token: str):
    target_payload = {
        "first_name": "Reset",
        "last_name": "Pass",
        "email": "resetpass@example.com",
        "phone": "+998900000014",
        "role": "client",
    }
    create_resp = await client.post(
        "/api/v1/users/",
        json=target_payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    target_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/users/{target_id}/reset-password",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "temporary_password" in data
    assert len(data["temporary_password"]) == 6


@pytest.mark.asyncio
async def test_admin_cannot_create_super_admin(client: AsyncClient, admin_token: str):
    payload = {
        "first_name": "Bad",
        "last_name": "Admin",
        "email": "badadmin@example.com",
        "phone": "+998900000015",
        "role": "super_admin",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_create_admin(client: AsyncClient, super_admin_token: str):
    payload = {
        "first_name": "New",
        "last_name": "Admin",
        "email": "newadmin@example.com",
        "phone": "+998900000016",
        "role": "admin",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_admin_cannot_delete_super_admin(client: AsyncClient, admin_token: str, super_admin_token: str):
    response = await client.delete(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 405


@pytest.mark.asyncio
async def test_login_with_phone(client: AsyncClient, admin_token: str):
    login_payload = {
        "phone": "+998901234501",
        "password": "StrongPass1",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
