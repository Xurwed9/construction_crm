import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient, admin_token: str):
    payload = {"name": "Sunny Residential Complex", "description": "Luxury complex", "address": "123 Main St"}
    response = await client.post(
        "/api/v1/matrix/projects",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Sunny Residential Complex"
    assert data["status"] == "active"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(client: AsyncClient, admin_token: str):
    response = await client.get(
        "/api/v1/matrix/projects",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Get Project Test"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = create_resp.json()["id"]

    response = await client.get(
        f"/api/v1/matrix/projects/{project_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Get Project Test"


@pytest.mark.asyncio
async def test_update_project(client: AsyncClient, admin_token: str):
    create_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Old Name"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/matrix/projects/{project_id}",
        json={"name": "New Name", "status": "archived"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_create_building(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Building Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]

    payload = {"project_id": project_id, "name": "Tower A", "number_of_sections": 2, "floors_count": 10}
    response = await client.post(
        "/api/v1/matrix/buildings",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Tower A"
    assert data["number_of_sections"] == 2


@pytest.mark.asyncio
async def test_get_building(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Get Building Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower B", "number_of_sections": 1, "floors_count": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    response = await client.get(
        f"/api/v1/matrix/buildings/{building_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Tower B"


@pytest.mark.asyncio
async def test_create_floor(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Floor Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower C", "number_of_sections": 1, "floors_count": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    response = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["number"] == 1


@pytest.mark.asyncio
async def test_create_floor_duplicate(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Duplicate Floor Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower D", "number_of_sections": 1, "floors_count": 10},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_section(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Section Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower E", "number_of_sections": 3, "floors_count": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    response = await client.post(
        "/api/v1/matrix/sections",
        json={"building_id": building_id, "name": "Section A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Section A"


@pytest.mark.asyncio
async def test_create_apartment(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Apartment Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower F", "number_of_sections": 1, "floors_count": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    floor_resp = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    floor_id = floor_resp.json()["id"]

    payload = {
        "floor_id": floor_id,
        "number": "101",
        "rooms": 2,
        "area": 65.5,
        "price": 150000.0,
        "currency": "USD",
        "direction": "north",
    }
    response = await client.post(
        "/api/v1/matrix/apartments",
        json=payload,
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["number"] == "101"
    assert data["rooms"] == 2
    assert data["status"] == "available"


@pytest.mark.asyncio
async def test_reserve_apartment(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Reserve Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower G", "number_of_sections": 1, "floors_count": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]
    floor_resp = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    floor_id = floor_resp.json()["id"]
    apt_resp = await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "201", "rooms": 3, "area": 80.0, "price": 200000.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    apartment_id = apt_resp.json()["id"]

    response = await client.post(
        "/api/v1/matrix/reserve",
        json={"apartment_id": apartment_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "reserved"


@pytest.mark.asyncio
async def test_double_reservation_fails(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Double Reserve Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower H", "number_of_sections": 1, "floors_count": 5},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]
    floor_resp = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    floor_id = floor_resp.json()["id"]
    apt_resp = await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "301", "rooms": 1, "area": 45.0, "price": 100000.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    apartment_id = apt_resp.json()["id"]

    await client.post(
        "/api/v1/matrix/reserve",
        json={"apartment_id": apartment_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    response = await client.post(
        "/api/v1/matrix/reserve",
        json={"apartment_id": apartment_id},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_matrix(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Matrix Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower Matrix", "number_of_sections": 2, "floors_count": 3},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    section_a_resp = await client.post(
        "/api/v1/matrix/sections",
        json={"building_id": building_id, "name": "Section A"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    section_a_id = section_a_resp.json()["id"]
    section_b_resp = await client.post(
        "/api/v1/matrix/sections",
        json={"building_id": building_id, "name": "Section B"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    section_b_id = section_b_resp.json()["id"]

    for floor_num in range(1, 4):
        floor_resp = await client.post(
            "/api/v1/matrix/floors",
            json={"building_id": building_id, "number": floor_num},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        floor_id = floor_resp.json()["id"]

        for sec_id, sec_suffix in [(section_a_id, "A"), (section_b_id, "B")]:
            await client.post(
                "/api/v1/matrix/apartments",
                json={
                    "floor_id": floor_id,
                    "section_id": sec_id,
                    "number": f"{floor_num}0{sec_suffix}",
                    "rooms": 2,
                    "area": 70.0,
                    "price": 180000.0,
                },
                headers={"Authorization": f"Bearer {admin_token}"},
            )

    response = await client.get(
        f"/api/v1/matrix/matrix/{building_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["building_name"] == "Tower Matrix"
    assert len(data["sections"]) == 2
    assert data["sections"][0]["section_name"] == "Section A"


@pytest.mark.asyncio
async def test_get_statistics(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Stats Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower Stats", "number_of_sections": 1, "floors_count": 2},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]
    floor_resp = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    floor_id = floor_resp.json()["id"]

    await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "A1", "rooms": 1, "area": 40.0, "price": 80000.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "A2", "rooms": 2, "area": 60.0, "price": 120000.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        f"/api/v1/matrix/statistics/{building_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_apartments"] == 2
    assert data["total_revenue"] > 0


@pytest.mark.asyncio
async def test_manager_cannot_create_project(client: AsyncClient, manager_token: str):
    payload = {"name": "Manager Project"}
    response = await client.post(
        "/api/v1/matrix/projects",
        json=payload,
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_can_view_matrix(client: AsyncClient, admin_token: str, manager_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Manager View Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower M", "number_of_sections": 1, "floors_count": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]

    response = await client.get(
        f"/api/v1/matrix/matrix/{building_id}",
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_client_cannot_access_matrix(client: AsyncClient, client_token: str):
    response = await client.get(
        "/api/v1/matrix/projects",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_filter_apartments_by_rooms(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Filter Test Project"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower Filter", "number_of_sections": 1, "floors_count": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    building_id = build_resp.json()["id"]
    floor_resp = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    floor_id = floor_resp.json()["id"]

    await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "S1", "rooms": 1, "area": 35.0, "price": 50000.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "S2", "rooms": 2, "area": 55.0, "price": 90000.0},
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = await client.get(
        f"/api/v1/matrix/apartments?rooms=1&building_id={building_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
