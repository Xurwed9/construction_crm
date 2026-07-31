import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.lead import Lead, LeadNote, LeadTimeline
from app.models.user import User, UserRole

LEAD_PAYLOAD = {
    "first_name": "John",
    "last_name": "Smith",
    "phone": "+998901110001",
    "email": "john.smith@example.com",
    "budget": 150000.0,
    "priority": "medium",
    "lead_source": "instagram",
    "notes": "Interested in 2-bedroom apartment",
}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _user_id_from_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload["sub"]


@pytest_asyncio.fixture(autouse=True)
async def clean_leads(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(LeadTimeline))
        await session.execute(delete(LeadNote))
        await session.execute(delete(Lead))
        await session.commit()
    yield


@pytest_asyncio.fixture
async def second_manager(engine) -> dict:
    uid = uuid.uuid4().hex[:6]
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            first_name="Manager",
            last_name=f"Two{uid}",
            email=f"manager_two_{uid}@test.com",
            phone=f"+99890123{int(uid[:6], 16) % 100000:05d}",
            password_hash=hash_password("StrongPass1"),
            role=UserRole.MANAGER,
        )
        session.add(user)
        await session.commit()
        return {"id": str(user.id), "token": create_access_token(str(user.id), user.role.value)}


async def _create_lead(client: AsyncClient, token: str, **overrides) -> dict:
    payload = {**LEAD_PAYLOAD, **overrides}
    response = await client.post("/api/v1/leads", json=payload, headers=_auth(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_lead(client: AsyncClient, admin_token: str):
    data = await _create_lead(client, admin_token)
    assert data["full_name"] == "John Smith"
    assert data["status"] == "new"
    assert data["priority"] == "medium"
    assert data["assigned_manager"] is None
    assert "id" in data


@pytest.mark.asyncio
async def test_create_lead_manager_auto_assigned(client: AsyncClient, manager_token: str):
    data = await _create_lead(client, manager_token)
    assert data["assigned_manager_id"] == _user_id_from_token(manager_token)
    assert data["assigned_manager"]["role"] == "manager"


@pytest.mark.asyncio
async def test_create_lead_invalid_phone(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/leads",
        json={**LEAD_PAYLOAD, "phone": "not-a-phone"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_invalid_email(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/api/v1/leads",
        json={**LEAD_PAYLOAD, "email": "not-an-email"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_lead_invalid_manager(client: AsyncClient, admin_token: str, client_token: str):
    client_id = _user_id_from_token(client_token)
    response = await client.post(
        "/api/v1/leads",
        json={**LEAD_PAYLOAD, "assigned_manager_id": client_id},
        headers=_auth(admin_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_lead_assign_manager(client: AsyncClient, admin_token: str, manager_token: str):
    data = await _create_lead(
        client,
        admin_token,
        assigned_manager_id=_user_id_from_token(manager_token),
    )
    assert data["assigned_manager_id"] == _user_id_from_token(manager_token)


@pytest.mark.asyncio
async def test_get_lead(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.get(f"/api/v1/leads/{created['id']}", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["full_name"] == "John Smith"
    assert response.json()["notes"] == "Interested in 2-bedroom apartment"


@pytest.mark.asyncio
async def test_get_lead_not_found(client: AsyncClient, admin_token: str):
    response = await client.get(f"/api/v1/leads/{uuid.uuid4()}", headers=_auth(admin_token))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_leads_pagination(client: AsyncClient, admin_token: str):
    for i in range(3):
        await _create_lead(client, admin_token, phone=f"+99890111000{i + 2}")

    response = await client.get("/api/v1/leads?page=1&size=2", headers=_auth(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) == 2
    assert data["total"] >= 3
    assert data["page"] == 1
    assert data["size"] == 2
    assert data["pages"] >= 2


@pytest.mark.asyncio
async def test_update_lead_recomputes_full_name(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.patch(
        f"/api/v1/leads/{created['id']}",
        json={"first_name": "Jane", "budget": 200000.0},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["full_name"] == "Jane Smith"
    assert data["budget"] == 200000.0


@pytest.mark.asyncio
async def test_update_lead_not_found(client: AsyncClient, admin_token: str):
    response = await client.patch(
        f"/api/v1/leads/{uuid.uuid4()}",
        json={"first_name": "X"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_lead(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.delete(f"/api/v1/leads/{created['id']}", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["message"] == "Lead deleted successfully"

    get_resp = await client.get(f"/api/v1/leads/{created['id']}", headers=_auth(admin_token))
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_kanban_groups_by_status(client: AsyncClient, admin_token: str):
    lead1 = await _create_lead(client, admin_token, phone="+998901110050")
    lead2 = await _create_lead(client, admin_token, phone="+998901110051")
    lead3 = await _create_lead(client, admin_token, phone="+998901110052")

    await client.patch(
        f"/api/v1/leads/{lead1['id']}/status",
        json={"status": "first_call"},
        headers=_auth(admin_token),
    )
    await client.patch(
        f"/api/v1/leads/{lead3['id']}/status",
        json={"status": "first_call"},
        headers=_auth(admin_token),
    )

    response = await client.get("/api/v1/leads/kanban", headers=_auth(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {
        "new",
        "first_call",
        "consultation",
        "office_visit",
        "presentation",
        "decision",
        "reservation",
        "contract",
        "payment",
        "completed",
        "lost",
    }
    assert len(data["new"]) == 1
    assert data["new"][0]["id"] == lead2["id"]
    assert len(data["first_call"]) == 2
    assert {lead["id"] for lead in data["first_call"]} == {lead1["id"], lead3["id"]}


@pytest.mark.asyncio
async def test_move_lead_valid_transition(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.patch(
        f"/api/v1/leads/{created['id']}/status",
        json={"status": "first_call"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "first_call"


@pytest.mark.asyncio
async def test_move_lead_invalid_transition(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.patch(
        f"/api/v1/leads/{created['id']}/status",
        json={"status": "contract"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_move_lead_back_and_lost_to_new(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)

    resp = await client.patch(
        f"/api/v1/leads/{created['id']}/status",
        json={"status": "lost"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "lost"

    resp = await client.patch(
        f"/api/v1/leads/{created['id']}/status",
        json={"status": "new"},
        headers=_auth(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "new"


@pytest.mark.asyncio
async def test_assign_manager(client: AsyncClient, admin_token: str, manager_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.patch(
        f"/api/v1/leads/{created['id']}/manager",
        json={"assigned_manager_id": _user_id_from_token(manager_token)},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["assigned_manager_id"] == _user_id_from_token(manager_token)


@pytest.mark.asyncio
async def test_assign_manager_not_found(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    response = await client.patch(
        f"/api/v1/leads/{created['id']}/manager",
        json={"assigned_manager_id": str(uuid.uuid4())},
        headers=_auth(admin_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_note_crud_flow(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    lead_id = created["id"]

    add_resp = await client.post(
        f"/api/v1/leads/{lead_id}/notes",
        json={"content": "Called the client, wants a tour"},
        headers=_auth(admin_token),
    )
    assert add_resp.status_code == 201
    note_id = add_resp.json()["id"]
    assert add_resp.json()["content"] == "Called the client, wants a tour"

    list_resp = await client.get(f"/api/v1/leads/{lead_id}/notes", headers=_auth(admin_token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = await client.patch(
        f"/api/v1/leads/notes/{note_id}",
        json={"content": "Client cancelled the tour"},
        headers=_auth(admin_token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["content"] == "Client cancelled the tour"

    delete_resp = await client.delete(f"/api/v1/leads/notes/{note_id}", headers=_auth(admin_token))
    assert delete_resp.status_code == 200

    list_resp = await client.get(f"/api/v1/leads/{lead_id}/notes", headers=_auth(admin_token))
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 0


@pytest.mark.asyncio
async def test_note_not_found(client: AsyncClient, admin_token: str):
    response = await client.patch(
        f"/api/v1/leads/notes/{uuid.uuid4()}",
        json={"content": "x"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_timeline_records_actions(client: AsyncClient, admin_token: str):
    created = await _create_lead(client, admin_token)
    lead_id = created["id"]

    await client.patch(
        f"/api/v1/leads/{lead_id}/status",
        json={"status": "first_call"},
        headers=_auth(admin_token),
    )
    await client.post(
        f"/api/v1/leads/{lead_id}/notes",
        json={"content": "First follow-up"},
        headers=_auth(admin_token),
    )

    response = await client.get(f"/api/v1/leads/{lead_id}/timeline", headers=_auth(admin_token))
    assert response.status_code == 200
    actions = [entry["action"] for entry in response.json()]
    assert actions == ["lead_created", "status_changed", "note_added"]


@pytest.mark.asyncio
async def test_search_by_phone(client: AsyncClient, admin_token: str):
    await _create_lead(client, admin_token)
    await _create_lead(client, admin_token, first_name="Alice", last_name="Wong", phone="+998901110060")

    response = await client.get("/api/v1/leads?search=1110060", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["first_name"] == "Alice"


@pytest.mark.asyncio
async def test_search_by_name(client: AsyncClient, admin_token: str):
    await _create_lead(client, admin_token)
    response = await client.get("/api/v1/leads?search=John", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_search_by_email(client: AsyncClient, admin_token: str):
    await _create_lead(client, admin_token, phone="+998901110070")
    response = await client.get("/api/v1/leads?search=john.smith", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_filter_by_status_and_priority(client: AsyncClient, admin_token: str):
    lead = await _create_lead(client, admin_token, phone="+998901110080", priority="urgent")
    await client.patch(
        f"/api/v1/leads/{lead['id']}/status",
        json={"status": "first_call"},
        headers=_auth(admin_token),
    )
    await client.patch(
        f"/api/v1/leads/{lead['id']}/status",
        json={"status": "consultation"},
        headers=_auth(admin_token),
    )

    status_resp = await client.get("/api/v1/leads?status=consultation", headers=_auth(admin_token))
    assert status_resp.json()["total"] == 1

    priority_resp = await client.get("/api/v1/leads?status=consultation&priority=urgent", headers=_auth(admin_token))
    assert priority_resp.json()["total"] == 1

    combo_resp = await client.get("/api/v1/leads?status=consultation&priority=low", headers=_auth(admin_token))
    assert combo_resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_filter_by_manager_and_lead_source(client: AsyncClient, admin_token: str, manager_token: str):
    manager_id = _user_id_from_token(manager_token)
    await _create_lead(client, admin_token, phone="+998901110090", assigned_manager_id=manager_id)
    await _create_lead(client, admin_token, phone="+998901110091", lead_source="facebook")

    mgr_resp = await client.get(f"/api/v1/leads?manager_id={manager_id}", headers=_auth(admin_token))
    assert mgr_resp.json()["total"] == 1

    src_resp = await client.get("/api/v1/leads?lead_source=facebook", headers=_auth(admin_token))
    assert src_resp.json()["total"] == 1


@pytest.mark.asyncio
async def test_filter_by_date_range(client: AsyncClient, admin_token: str):
    await _create_lead(client, admin_token, phone="+998901110100")
    response = await client.get(
        "/api/v1/leads?date_from=2020-01-01T00:00:00&date_to=2030-01-01T00:00:00",
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1


@pytest.mark.asyncio
async def test_sort_by_budget(client: AsyncClient, admin_token: str):
    await _create_lead(client, admin_token, phone="+998901110110", budget=50000.0)
    await _create_lead(client, admin_token, phone="+998901110111", budget=200000.0)
    await _create_lead(client, admin_token, phone="+998901110112", budget=100000.0)

    response = await client.get("/api/v1/leads?sort=budget", headers=_auth(admin_token))
    assert response.status_code == 200
    budgets = [item["budget"] for item in response.json()["items"][:3]]
    assert budgets == [200000.0, 100000.0, 50000.0]


@pytest.mark.asyncio
async def test_sort_by_priority(client: AsyncClient, admin_token: str):
    await _create_lead(client, admin_token, phone="+998901110120", priority="low")
    await _create_lead(client, admin_token, phone="+998901110121", priority="urgent")
    await _create_lead(client, admin_token, phone="+998901110122", priority="high")

    response = await client.get("/api/v1/leads?sort=priority", headers=_auth(admin_token))
    assert response.status_code == 200
    priorities = [item["priority"] for item in response.json()["items"][:3]]
    assert priorities == ["urgent", "high", "low"]


@pytest.mark.asyncio
async def test_invalid_sort_option(client: AsyncClient, admin_token: str):
    response = await client.get("/api/v1/leads?sort=banana", headers=_auth(admin_token))
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lead_with_project_links(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Lead Link Project"},
        headers=_auth(admin_token),
    )
    project_id = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": "Tower L", "number_of_sections": 1, "floors_count": 1},
        headers=_auth(admin_token),
    )
    building_id = build_resp.json()["id"]
    floor_resp = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers=_auth(admin_token),
    )
    floor_id = floor_resp.json()["id"]
    apt_resp = await client.post(
        "/api/v1/matrix/apartments",
        json={"floor_id": floor_id, "number": "L1", "rooms": 2, "area": 60.0, "price": 120000.0},
        headers=_auth(admin_token),
    )
    apartment_id = apt_resp.json()["id"]

    data = await _create_lead(
        client,
        admin_token,
        phone="+998901110130",
        project_id=project_id,
        building_id=building_id,
        apartment_id=apartment_id,
    )
    assert data["project_id"] == project_id
    assert data["building_id"] == building_id
    assert data["apartment_id"] == apartment_id


@pytest.mark.asyncio
async def test_lead_project_link_mismatch(client: AsyncClient, admin_token: str):
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Mismatch P1"},
        headers=_auth(admin_token),
    )
    p1 = proj_resp.json()["id"]
    proj_resp = await client.post(
        "/api/v1/matrix/projects",
        json={"name": "Mismatch P2"},
        headers=_auth(admin_token),
    )
    p2 = proj_resp.json()["id"]
    build_resp = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": p2, "name": "Tower M", "number_of_sections": 1, "floors_count": 1},
        headers=_auth(admin_token),
    )
    b2 = build_resp.json()["id"]

    response = await client.post(
        "/api/v1/leads",
        json={**LEAD_PAYLOAD, "phone": "+998901110131", "project_id": p1, "building_id": b2},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_client_cannot_access_leads(client: AsyncClient, client_token: str):
    response = await client.get("/api/v1/leads", headers=_auth(client_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_cannot_create_lead(client: AsyncClient, client_token: str):
    response = await client.post("/api/v1/leads", json=LEAD_PAYLOAD, headers=_auth(client_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_delete_lead(client: AsyncClient, manager_token: str):
    created = await _create_lead(client, manager_token)
    response = await client.delete(f"/api/v1/leads/{created['id']}", headers=_auth(manager_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_assign_manager(client: AsyncClient, manager_token: str):
    created = await _create_lead(client, manager_token)
    response = await client.patch(
        f"/api/v1/leads/{created['id']}/manager",
        json={"assigned_manager_id": _user_id_from_token(manager_token)},
        headers=_auth(manager_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_sees_only_own_leads(client: AsyncClient, manager_token: str, second_manager: dict):
    await _create_lead(client, manager_token, phone="+998901110140")
    await _create_lead(client, second_manager["token"], phone="+998901110141")

    response = await client.get("/api/v1/leads", headers=_auth(manager_token))
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["phone"] == "+998901110140"


@pytest.mark.asyncio
async def test_manager_cannot_access_other_lead(client: AsyncClient, manager_token: str, second_manager: dict):
    created = await _create_lead(client, second_manager["token"], phone="+998901110150")

    response = await client.get(f"/api/v1/leads/{created['id']}", headers=_auth(manager_token))
    assert response.status_code == 403

    update_resp = await client.patch(
        f"/api/v1/leads/{created['id']}",
        json={"notes": "hacked"},
        headers=_auth(manager_token),
    )
    assert update_resp.status_code == 403

    move_resp = await client.patch(
        f"/api/v1/leads/{created['id']}/status",
        json={"status": "first_call"},
        headers=_auth(manager_token),
    )
    assert move_resp.status_code == 403


@pytest.mark.asyncio
async def test_manager_notes_only_own_lead(client: AsyncClient, manager_token: str, second_manager: dict):
    created = await _create_lead(client, second_manager["token"], phone="+998901110160")

    response = await client.post(
        f"/api/v1/leads/{created['id']}/notes",
        json={"content": "unauthorized note"},
        headers=_auth(manager_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_note_edit_by_other_manager_forbidden(client: AsyncClient, manager_token: str, second_manager: dict):
    created = await _create_lead(client, manager_token, phone="+998901110170")
    add_resp = await client.post(
        f"/api/v1/leads/{created['id']}/notes",
        json={"content": "private note"},
        headers=_auth(manager_token),
    )
    note_id = add_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/leads/notes/{note_id}",
        json={"content": "hacked"},
        headers=_auth(second_manager["token"]),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_kanban_scoped(client: AsyncClient, manager_token: str, second_manager: dict):
    await _create_lead(client, manager_token, phone="+998901110180")
    await _create_lead(client, second_manager["token"], phone="+998901110181")

    response = await client.get("/api/v1/leads/kanban", headers=_auth(manager_token))
    assert response.status_code == 200
    data = response.json()
    total = sum(len(column) for column in data.values())
    assert total == 1
