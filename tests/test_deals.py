import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.deal import Deal
from app.models.deal_activity import DealActivity
from app.models.deal_document import DealDocument
from app.models.deal_payment import DealPayment
from app.models.deal_task import DealTask
from app.models.deal_timeline import DealTimeline
from app.models.matrix import Apartment, ApartmentStatus
from app.models.user import User, UserRole


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _user_id_from_token(token: str) -> str:
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return payload["sub"]


@pytest_asyncio.fixture
async def second_manager_token(engine) -> str:
    uid = uuid.uuid4().hex[:6]
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            first_name="Manager",
            last_name=f"Two{uid}",
            email=f"deal_manager_two_{uid}@test.com",
            phone=f"+99890123{uuid.uuid4().int % 100000:05d}",
            password_hash=hash_password("StrongPass1"),
            role=UserRole.MANAGER,
        )
        session.add(user)
        await session.commit()
        return create_access_token(str(user.id), user.role.value)


@pytest_asyncio.fixture
async def second_client_token(engine) -> str:
    uid = uuid.uuid4().hex[:6]
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        user = User(
            first_name="Client",
            last_name=f"Two{uid}",
            email=f"deal_client_two_{uid}@test.com",
            phone=f"+99890123{uuid.uuid4().int % 100000:05d}",
            password_hash=hash_password("StrongPass1"),
            role=UserRole.CLIENT,
        )
        session.add(user)
        await session.commit()
        return create_access_token(str(user.id), user.role.value)


@pytest_asyncio.fixture(autouse=True)
async def clean_deals(engine):
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        await session.execute(delete(DealPayment))
        await session.execute(delete(DealDocument))
        await session.execute(delete(DealTask))
        await session.execute(delete(DealActivity))
        await session.execute(delete(DealTimeline))
        await session.execute(delete(Deal))
        await session.execute(update(Apartment).values(status=ApartmentStatus.AVAILABLE, deal_id=None))
        await session.commit()
    yield


async def _create_apartment(client: AsyncClient, token: str) -> dict:
    suffix = uuid.uuid4().hex[:6]
    proj = await client.post(
        "/api/v1/matrix/projects",
        json={"name": f"Proj {suffix}"},
        headers=_auth(token),
    )
    assert proj.status_code == 201, proj.text
    project_id = proj.json()["id"]

    build = await client.post(
        "/api/v1/matrix/buildings",
        json={"project_id": project_id, "name": f"Tower {suffix}", "number_of_sections": 1, "floors_count": 5},
        headers=_auth(token),
    )
    assert build.status_code == 201, build.text
    building_id = build.json()["id"]

    floor = await client.post(
        "/api/v1/matrix/floors",
        json={"building_id": building_id, "number": 1},
        headers=_auth(token),
    )
    assert floor.status_code == 201, floor.text
    floor_id = floor.json()["id"]

    apt = await client.post(
        "/api/v1/matrix/apartments",
        json={
            "floor_id": floor_id,
            "number": f"A-{uuid.uuid4().hex[:4]}",
            "rooms": 2,
            "area": 60.0,
            "price": 100000.0,
            "currency": "USD",
        },
        headers=_auth(token),
    )
    assert apt.status_code == 201, apt.text
    data = apt.json()
    data["project_id"] = project_id
    data["building_id"] = building_id
    return data


async def _create_deal(
    client: AsyncClient, token: str, apartment: dict, client_id: str | None = None, **overrides
) -> dict:
    payload = {
        "apartment_id": apartment["id"],
        "price": apartment["price"],
        "project_id": apartment["project_id"],
        "building_id": apartment["building_id"],
        "client_id": client_id,
        "priority": "high",
    }
    payload.update(overrides)
    response = await client.post("/api/v1/deals", json=payload, headers=_auth(token))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_create_deal_with_apartment(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    assert deal["status"] == "new"
    assert deal["price"] == 100000.0
    assert deal["final_price"] == 100000.0
    assert deal["remaining_amount"] == 100000.0
    assert deal["paid_amount"] == 0.0
    assert deal["currency"] == "USD"
    assert deal["apartment_id"] == apartment["id"]
    assert deal["client_id"] == client_id
    assert deal["deal_number"].startswith("DL-")
    assert "created_at" in deal


@pytest.mark.asyncio
async def test_create_deal_manager_auto_assigned(
    client: AsyncClient, manager_token: str, admin_token: str, client_token: str
):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, manager_token, apartment, client_id)
    assert deal["manager_id"] == _user_id_from_token(manager_token)


@pytest.mark.asyncio
async def test_create_deal_requires_price_without_apartment(client: AsyncClient, admin_token: str, client_token: str):
    client_id = _user_id_from_token(client_token)
    response = await client.post(
        "/api/v1/deals",
        json={"client_id": client_id, "priority": "high"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_create_deal_price_defaults_from_apartment(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    response = await client.post(
        "/api/v1/deals",
        json={"apartment_id": apartment["id"], "client_id": client_id},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201
    assert response.json()["price"] == 100000.0


@pytest.mark.asyncio
async def test_create_deal_discount_exceeds_price(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    response = await client.post(
        "/api/v1/deals",
        json={
            "apartment_id": apartment["id"],
            "price": 100000.0,
            "discount": 150000.0,
            "client_id": client_id,
        },
        headers=_auth(admin_token),
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_create_deal_duplicate_apartment_conflict(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    await _create_deal(client, admin_token, apartment, client_id)

    response = await client.post(
        "/api/v1/deals",
        json={"apartment_id": apartment["id"], "price": 100000.0, "client_id": client_id},
        headers=_auth(admin_token),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_deal_sold_apartment_conflict(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    await client.post(f"/api/v1/deals/{deal['id']}/close", json={}, headers=_auth(admin_token))

    response = await client.post(
        "/api/v1/deals",
        json={"apartment_id": apartment["id"], "price": 100000.0, "client_id": client_id},
        headers=_auth(admin_token),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_create_deal_from_lead(client: AsyncClient, admin_token: str, client_token: str):
    lead = await client.post(
        "/api/v1/leads",
        json={
            "first_name": "Lead",
            "last_name": "Client",
            "phone": f"+99890{uuid.uuid4().int % 100000000:08d}",
            "email": f"lead{uuid.uuid4().hex[:6]}@example.com",
            "budget": 150000.0,
        },
        headers=_auth(admin_token),
    )
    assert lead.status_code == 201, lead.text
    lead_id = lead.json()["id"]

    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id, lead_id=lead_id)

    timeline = await client.get(f"/api/v1/deals/{deal['id']}/timeline", headers=_auth(admin_token))
    assert timeline.status_code == 200
    events = [entry["event"] for entry in timeline.json()]
    assert "lead_converted" in events
    assert "deal_created" in events


@pytest.mark.asyncio
async def test_get_deal(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.get(f"/api/v1/deals/{deal['id']}", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["id"] == deal["id"]
    assert response.json()["apartment"]["id"] == apartment["id"]


@pytest.mark.asyncio
async def test_get_deal_not_found(client: AsyncClient, admin_token: str):
    response = await client.get(f"/api/v1/deals/{uuid.uuid4()}", headers=_auth(admin_token))
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_deals_search_by_deal_number(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.get(
        f"/api/v1/deals?search={deal['deal_number']}",
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == deal["id"]


@pytest.mark.asyncio
async def test_list_deals_search_by_client_name(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.get("/api/v1/deals?search=Client", headers=_auth(admin_token))
    assert response.status_code == 200
    assert any(item["id"] == deal["id"] for item in response.json()["items"])


@pytest.mark.asyncio
async def test_list_deals_filter_status_and_pagination(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    await _create_deal(client, admin_token, apartment, client_id)

    response = await client.get("/api/v1/deals?status=sold&page=1&size=5", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["total"] == 0
    assert response.json()["pages"] == 0

    response = await client.get("/api/v1/deals?status=new&sort=price", headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_update_deal_recalculates_financials(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"price": 120000.0, "discount": 20000.0, "priority": "urgent"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["price"] == 120000.0
    assert data["discount"] == 20000.0
    assert data["final_price"] == 100000.0
    assert data["remaining_amount"] == 100000.0
    assert data["priority"] == "urgent"


@pytest.mark.asyncio
async def test_update_deal_invalid_status_transition(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"status": "sold"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_deal_status_to_contract_generates_number(
    client: AsyncClient, admin_token: str, client_token: str
):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    response = await client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"status": "contract"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "contract"
    assert data["contract_number"].startswith("CNTR-")


@pytest.mark.asyncio
async def test_reserve_deal_marks_apartment_reserved(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "reserved"
    assert data["reservation_until"] is not None
    assert data["reservation_expired"] is False

    apt = await client.get(f"/api/v1/matrix/apartments/{apartment['id']}", headers=_auth(admin_token))
    assert apt.json()["status"] == "reserved"
    assert apt.json()["deal_id"] == deal["id"]


@pytest.mark.asyncio
async def test_reserve_deal_past_date_rejected(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.post(
        f"/api/v1/deals/{deal['id']}/reserve",
        json={"reservation_until": "2000-01-01T00:00:00Z"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_reserve_deal_second_deal_conflict(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal_a = await _create_deal(client, admin_token, apartment, client_id)
    await client.post(f"/api/v1/deals/{deal_a['id']}/reserve", json={}, headers=_auth(admin_token))

    response = await client.post(
        "/api/v1/deals",
        json={"apartment_id": apartment["id"], "price": 100000.0, "client_id": client_id},
        headers=_auth(admin_token),
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_close_deal_marks_apartment_sold(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    response = await client.post(
        f"/api/v1/deals/{deal['id']}/close",
        json={"contract_number": "CNTR-TEST-1"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "sold"
    assert data["contract_number"] == "CNTR-TEST-1"
    assert data["closed_at"] is not None

    apt = await client.get(f"/api/v1/matrix/apartments/{apartment['id']}", headers=_auth(admin_token))
    assert apt.json()["status"] == "sold"
    assert apt.json()["deal_id"] == deal["id"]


@pytest.mark.asyncio
async def test_close_deal_from_new_rejected(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.post(f"/api/v1/deals/{deal['id']}/close", json={}, headers=_auth(admin_token))
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_cancel_deal_releases_apartment(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    response = await client.post(
        f"/api/v1/deals/{deal['id']}/cancel",
        json={"cancel_reason": "Client changed their mind"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"
    assert response.json()["cancel_reason"] == "Client changed their mind"

    apt = await client.get(f"/api/v1/matrix/apartments/{apartment['id']}", headers=_auth(admin_token))
    assert apt.json()["status"] == "available"
    assert apt.json()["deal_id"] is None


@pytest.mark.asyncio
async def test_cancel_sold_deal_rejected(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    await client.post(f"/api/v1/deals/{deal['id']}/close", json={}, headers=_auth(admin_token))

    response = await client.post(
        f"/api/v1/deals/{deal['id']}/cancel",
        json={"cancel_reason": "test"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_restore_deal(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(
        f"/api/v1/deals/{deal['id']}/cancel",
        json={"cancel_reason": "test"},
        headers=_auth(admin_token),
    )
    response = await client.post(f"/api/v1/deals/{deal['id']}/restore", json={}, headers=_auth(admin_token))
    assert response.status_code == 200
    assert response.json()["status"] == "new"


@pytest.mark.asyncio
async def test_soft_delete_deal(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.delete(f"/api/v1/deals/{deal['id']}", headers=_auth(admin_token))
    assert response.status_code == 200

    response = await client.get(f"/api/v1/deals/{deal['id']}", headers=_auth(admin_token))
    assert response.status_code == 404

    response = await client.get("/api/v1/deals", headers=_auth(admin_token))
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_deal_timeline_records_events(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))

    response = await client.get(f"/api/v1/deals/{deal['id']}/timeline", headers=_auth(admin_token))
    assert response.status_code == 200
    events = [entry["event"] for entry in response.json()]
    assert "deal_created" in events
    assert "reservation" in events


@pytest.mark.asyncio
async def test_activity_crud(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    create = await client.post(
        f"/api/v1/deals/{deal['id']}/activities",
        json={"activity_type": "call", "content": "Called the client", "is_public": True},
        headers=_auth(admin_token),
    )
    assert create.status_code == 201, create.text
    activity_id = create.json()["id"]
    assert create.json()["actor"]["role"] == "admin"

    listed = await client.get(f"/api/v1/deals/{deal['id']}/activities", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert any(item["id"] == activity_id for item in listed.json())

    updated = await client.patch(
        f"/api/v1/activities/{activity_id}",
        json={"content": "Updated note", "completed": True},
        headers=_auth(admin_token),
    )
    assert updated.status_code == 200
    assert updated.json()["content"] == "Updated note"
    assert updated.json()["completed"] is True

    deleted = await client.delete(f"/api/v1/activities/{activity_id}", headers=_auth(admin_token))
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_client_sees_only_public_activities(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(
        f"/api/v1/deals/{deal['id']}/activities",
        json={"activity_type": "internal_note", "content": "secret", "is_public": False},
        headers=_auth(admin_token),
    )
    await client.post(
        f"/api/v1/deals/{deal['id']}/activities",
        json={"activity_type": "public_note", "content": "public", "is_public": True},
        headers=_auth(admin_token),
    )

    response = await client.get(f"/api/v1/deals/{deal['id']}/activities", headers=_auth(client_token))
    assert response.status_code == 200
    contents = [item["content"] for item in response.json()]
    assert "public" in contents
    assert "secret" not in contents


@pytest.mark.asyncio
async def test_task_crud_and_completion(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    create = await client.post(
        f"/api/v1/deals/{deal['id']}/tasks",
        json={"title": "Send documents", "priority": "high"},
        headers=_auth(admin_token),
    )
    assert create.status_code == 201, create.text
    task_id = create.json()["id"]
    assert create.json()["completed"] is False

    completed = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"completed": True},
        headers=_auth(admin_token),
    )
    assert completed.status_code == 200
    assert completed.json()["completed"] is True
    assert completed.json()["completed_at"] is not None

    listed = await client.get(f"/api/v1/deals/{deal['id']}/tasks", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert any(item["id"] == task_id for item in listed.json())

    deleted = await client.delete(f"/api/v1/tasks/{task_id}", headers=_auth(admin_token))
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_document_upload_and_delete(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    upload = await client.post(
        f"/api/v1/deals/{deal['id']}/documents",
        data={"document_type": "contract", "title": "Contract v1"},
        files={"file": ("contract.pdf", b"%PDF-1.4 test content", "application/pdf")},
        headers=_auth(admin_token),
    )
    assert upload.status_code == 201, upload.text
    doc = upload.json()
    assert doc["file_name"] == "contract.pdf"
    assert doc["document_type"] == "contract"
    assert doc["file_size"] > 0

    listed = await client.get(f"/api/v1/deals/{deal['id']}/documents", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert any(item["id"] == doc["id"] for item in listed.json())

    deleted = await client.delete(f"/api/v1/documents/{doc['id']}", headers=_auth(admin_token))
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_payment_updates_totals(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.post(
        f"/api/v1/deals/{deal['id']}/payments",
        json={"amount": 40000.0, "payment_method": "cash", "note": "First installment"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 201, response.text

    deal_resp = await client.get(f"/api/v1/deals/{deal['id']}", headers=_auth(admin_token))
    assert deal_resp.json()["paid_amount"] == 40000.0
    assert deal_resp.json()["remaining_amount"] == 60000.0

    listed = await client.get(f"/api/v1/deals/{deal['id']}/payments", headers=_auth(admin_token))
    assert listed.status_code == 200
    assert listed.json()[0]["amount"] == 40000.0


@pytest.mark.asyncio
async def test_payment_overpay_rejected(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    response = await client.post(
        f"/api/v1/deals/{deal['id']}/payments",
        json={"amount": 1000000.0},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_payment_blocked_on_cancelled_deal(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(
        f"/api/v1/deals/{deal['id']}/cancel",
        json={"cancel_reason": "test"},
        headers=_auth(admin_token),
    )
    response = await client.post(
        f"/api/v1/deals/{deal['id']}/payments",
        json={"amount": 1000.0},
        headers=_auth(admin_token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_statistics(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))

    response = await client.get("/api/v1/deals/statistics", headers=_auth(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert data["total_deals"] == 1
    assert data["open_deals"] == 1
    assert data["reserved"] == 1
    assert data["sold"] == 0
    assert data["cancelled"] == 0
    assert data["deals_today"] == 1
    assert data["deals_this_month"] == 1
    assert data["revenue"] == 0.0
    assert data["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_statistics_sold_deal_revenue(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(f"/api/v1/deals/{deal['id']}/reserve", json={}, headers=_auth(admin_token))
    await client.post(f"/api/v1/deals/{deal['id']}/close", json={}, headers=_auth(admin_token))

    response = await client.get("/api/v1/deals/statistics", headers=_auth(admin_token))
    data = response.json()
    assert data["sold"] == 1
    assert data["open_deals"] == 0
    assert data["revenue"] == 100000.0
    assert data["conversion_rate"] == 100.0


@pytest.mark.asyncio
async def test_dashboard(client: AsyncClient, admin_token: str, client_token: str):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    await client.post(
        f"/api/v1/deals/{deal['id']}/activities",
        json={"activity_type": "call", "content": "call"},
        headers=_auth(admin_token),
    )

    response = await client.get("/api/v1/dashboard/deals", headers=_auth(admin_token))
    assert response.status_code == 200
    data = response.json()
    assert any(item["id"] == deal["id"] for item in data["recent_deals"])
    assert len(data["recent_activities"]) == 1


@pytest.mark.asyncio
async def test_manager_cannot_access_others_deals(
    client: AsyncClient, manager_token: str, second_manager_token: str, admin_token: str, client_token: str
):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, manager_token, apartment, client_id)

    response = await client.get(f"/api/v1/deals/{deal['id']}", headers=_auth(second_manager_token))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_manager_cannot_reassign_deal(
    client: AsyncClient, manager_token: str, second_manager_token: str, admin_token: str, client_token: str
):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    deal = await _create_deal(client, manager_token, apartment, client_id)

    response = await client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"manager_id": _user_id_from_token(second_manager_token)},
        headers=_auth(manager_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_client_read_only_own_deal(
    client: AsyncClient, admin_token: str, client_token: str, second_client_token: str
):
    apartment = await _create_apartment(client, admin_token)
    client_id = _user_id_from_token(client_token)
    other_client_id = _user_id_from_token(second_client_token)
    deal = await _create_deal(client, admin_token, apartment, client_id)

    own = await client.get(f"/api/v1/deals/{deal['id']}", headers=_auth(client_token))
    assert own.status_code == 200

    other = await client.get(f"/api/v1/deals/{deal['id']}", headers=_auth(second_client_token))
    assert other.status_code == 403

    denied = await client.patch(
        f"/api/v1/deals/{deal['id']}",
        json={"priority": "low"},
        headers=_auth(client_token),
    )
    assert denied.status_code == 403

    seen = await client.get("/api/v1/deals", headers=_auth(second_client_token))
    assert seen.status_code == 200
    assert all(item["client_id"] == other_client_id for item in seen.json()["items"])
