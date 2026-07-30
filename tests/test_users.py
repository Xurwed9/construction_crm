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
async def test_create_user_as_admin(client: AsyncClient, admin_token: str):
    payload = {
        "first_name": "New",
        "last_name": "User",
        "email": "newuser@example.com",
        "phone": "+998900000010",
        "password": "StrongPass1",
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


@pytest.mark.asyncio
async def test_client_cannot_list_users(client: AsyncClient, client_token: str):
    response = await client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_activate_deactivate_user(client: AsyncClient, admin_token: str):
    target_payload = {
        "first_name": "Target",
        "last_name": "User",
        "email": "target@example.com",
        "phone": "+998900000011",
        "password": "StrongPass1",
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
        "password": "StrongPass1",
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
async def test_change_role(
    client: AsyncClient, super_admin_token: str, admin_token: str
):
    target_payload = {
        "first_name": "Role",
        "last_name": "Change",
        "email": "rolechange@example.com",
        "phone": "+998900000013",
        "password": "StrongPass1",
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
        params={"new_role": "manager"},
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "manager"
