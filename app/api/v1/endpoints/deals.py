from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.dependencies.deals import require_deal_view
from app.models.deal import DealPaymentType, DealPriority, DealStatus
from app.models.deal_document import DealDocumentType
from app.models.user import User
from app.permissions.roles import (
    DEALS_ACTIVITIES,
    DEALS_CANCEL,
    DEALS_CLOSE,
    DEALS_CREATE,
    DEALS_DELETE,
    DEALS_DOCUMENTS,
    DEALS_PAYMENTS,
    DEALS_RESERVE,
    DEALS_RESTORE,
    DEALS_TASKS,
    DEALS_UPDATE,
)
from app.schemas.common import MessageResponse
from app.schemas.deal import (
    DealCancelRequest,
    DealCloseRequest,
    DealCreate,
    DealListResponse,
    DealRead,
    DealReserveRequest,
    DealUpdate,
)
from app.schemas.deal_activity import (
    DealActivityCreate,
    DealActivityRead,
    DealActivityUpdate,
)
from app.schemas.deal_dashboard import DashboardDeals
from app.schemas.deal_document import DealDocumentRead
from app.schemas.deal_payment import DealPaymentCreate, DealPaymentRead
from app.schemas.deal_statistics import DealStatistics
from app.schemas.deal_task import DealTaskCreate, DealTaskRead, DealTaskUpdate
from app.schemas.deal_timeline import DealTimelineRead
from app.services.deal import deal_service
from app.services.deal_activity import activity_service
from app.services.deal_analytics import analytics_service
from app.services.deal_dashboard import dashboard_service
from app.services.deal_document import document_service
from app.services.deal_task import task_service

router = APIRouter(prefix="/deals", tags=["Deal Management"])
activities_router = APIRouter(prefix="/activities", tags=["Deal Activities"])
tasks_router = APIRouter(prefix="/tasks", tags=["Deal Tasks"])
documents_router = APIRouter(prefix="/documents", tags=["Deal Documents"])
dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/statistics", response_model=DealStatistics)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await analytics_service.get_statistics(db, current_user)


@router.get("", response_model=DealListResponse)
async def list_deals(
    search: str | None = Query(None, min_length=1),
    status: DealStatus | None = None,
    priority: DealPriority | None = None,
    manager_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    building_id: uuid.UUID | None = None,
    apartment_id: uuid.UUID | None = None,
    payment_type: DealPaymentType | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = Query("newest", pattern="^(newest|oldest|price|remaining|created|updated)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    deals, total = await deal_service.list_deals(
        db,
        current_user,
        page=page,
        size=size,
        search=search,
        status=status,
        priority=priority,
        manager_id=manager_id,
        project_id=project_id,
        building_id=building_id,
        apartment_id=apartment_id,
        payment_type=payment_type,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    pages = (total + size - 1) // size
    return DealListResponse(
        items=[DealRead.model_validate(deal) for deal in deals],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


@router.post("", response_model=DealRead, status_code=201)
async def create_deal(
    data: DealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_CREATE)),
):
    return await deal_service.create_deal(db, current_user, data)


@router.get("/{deal_id}", response_model=DealRead)
async def get_deal(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await deal_service.get_deal(db, current_user, deal_id)


@router.patch("/{deal_id}", response_model=DealRead)
async def update_deal(
    deal_id: uuid.UUID,
    data: DealUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_UPDATE)),
):
    return await deal_service.update_deal(db, current_user, deal_id, data)


@router.delete("/{deal_id}", response_model=MessageResponse)
async def delete_deal(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_DELETE)),
):
    await deal_service.delete_deal(db, current_user, deal_id)
    return MessageResponse(message="Deal deleted successfully")


@router.post("/{deal_id}/reserve", response_model=DealRead)
async def reserve_deal(
    deal_id: uuid.UUID,
    data: DealReserveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_RESERVE)),
):
    return await deal_service.reserve_deal(db, current_user, deal_id, data)


@router.post("/{deal_id}/cancel", response_model=DealRead)
async def cancel_deal(
    deal_id: uuid.UUID,
    data: DealCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_CANCEL)),
):
    return await deal_service.cancel_deal(db, current_user, deal_id, data)


@router.post("/{deal_id}/close", response_model=DealRead)
async def close_deal(
    deal_id: uuid.UUID,
    data: DealCloseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_CLOSE)),
):
    return await deal_service.close_deal(db, current_user, deal_id, data)


@router.post("/{deal_id}/restore", response_model=DealRead)
async def restore_deal(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_RESTORE)),
):
    return await deal_service.restore_deal(db, current_user, deal_id)


@router.get("/{deal_id}/timeline", response_model=list[DealTimelineRead])
async def list_timeline(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await deal_service.list_timeline(db, current_user, deal_id)


@router.get("/{deal_id}/activities", response_model=list[DealActivityRead])
async def list_activities(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await activity_service.list(db, current_user, deal_id)


@router.post("/{deal_id}/activities", response_model=DealActivityRead, status_code=201)
async def create_activity(
    deal_id: uuid.UUID,
    data: DealActivityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_ACTIVITIES)),
):
    return await activity_service.create(db, current_user, deal_id, data)


@activities_router.patch("/{activity_id}", response_model=DealActivityRead)
async def update_activity(
    activity_id: uuid.UUID,
    data: DealActivityUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_ACTIVITIES)),
):
    return await activity_service.update(db, current_user, activity_id, data)


@activities_router.delete("/{activity_id}", response_model=MessageResponse)
async def delete_activity(
    activity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_ACTIVITIES)),
):
    await activity_service.delete(db, current_user, activity_id)
    return MessageResponse(message="Activity deleted successfully")


@router.get("/{deal_id}/tasks", response_model=list[DealTaskRead])
async def list_tasks(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await task_service.list(db, current_user, deal_id)


@router.post("/{deal_id}/tasks", response_model=DealTaskRead, status_code=201)
async def create_task(
    deal_id: uuid.UUID,
    data: DealTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_TASKS)),
):
    return await task_service.create(db, current_user, deal_id, data)


@tasks_router.patch("/{task_id}", response_model=DealTaskRead)
async def update_task(
    task_id: uuid.UUID,
    data: DealTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_TASKS)),
):
    return await task_service.update(db, current_user, task_id, data)


@tasks_router.delete("/{task_id}", response_model=MessageResponse)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_TASKS)),
):
    await task_service.delete(db, current_user, task_id)
    return MessageResponse(message="Task deleted successfully")


@router.get("/{deal_id}/documents", response_model=list[DealDocumentRead])
async def list_documents(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await document_service.list(db, current_user, deal_id)


@router.post("/{deal_id}/documents", response_model=DealDocumentRead, status_code=201)
async def upload_document(
    deal_id: uuid.UUID,
    document_type: DealDocumentType = Form(...),
    title: str = Form(..., min_length=1, max_length=255),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_DOCUMENTS)),
):
    return await document_service.create(db, current_user, deal_id, document_type, title, file)


@documents_router.delete("/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_DOCUMENTS)),
):
    await document_service.delete(db, current_user, document_id)
    return MessageResponse(message="Document deleted successfully")


@router.get("/{deal_id}/payments", response_model=list[DealPaymentRead])
async def list_payments(
    deal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await deal_service.list_payments(db, current_user, deal_id)


@router.post("/{deal_id}/payments", response_model=DealPaymentRead, status_code=201)
async def add_payment(
    deal_id: uuid.UUID,
    data: DealPaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(DEALS_PAYMENTS)),
):
    return await deal_service.add_payment(db, current_user, deal_id, data)


@dashboard_router.get("/deals", response_model=DashboardDeals)
async def get_dashboard_deals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_deal_view),
):
    return await dashboard_service.get_dashboard(db, current_user)
