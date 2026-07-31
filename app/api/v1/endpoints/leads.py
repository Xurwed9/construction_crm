import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.auth import require_permission
from app.models.lead import LeadPriority, LeadStatus
from app.models.user import User
from app.permissions.roles import (
    LEADS_ASSIGN,
    LEADS_CREATE,
    LEADS_DELETE,
    LEADS_MOVE,
    LEADS_NOTES,
    LEADS_UPDATE,
    LEADS_VIEW,
)
from app.schemas.common import MessageResponse
from app.schemas.lead import (
    LeadAssignManagerRequest,
    LeadCreate,
    LeadListResponse,
    LeadMoveRequest,
    LeadNoteCreate,
    LeadNoteRead,
    LeadNoteUpdate,
    LeadRead,
    LeadShortRead,
    LeadTimelineRead,
    LeadUpdate,
)
from app.services.lead import lead_service

router = APIRouter(prefix="/leads", tags=["Lead Management"])


@router.get("/kanban", response_model=dict[LeadStatus, list[LeadShortRead]])
async def get_kanban(
    search: str | None = Query(None, min_length=1),
    status: LeadStatus | None = None,
    priority: LeadPriority | None = None,
    manager_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    lead_source: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_VIEW)),
):
    return await lead_service.get_kanban(
        db,
        current_user,
        search=search,
        status=status,
        priority=priority,
        manager_id=manager_id,
        project_id=project_id,
        lead_source=lead_source,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("", response_model=LeadListResponse)
async def list_leads(
    search: str | None = Query(None, min_length=1),
    status: LeadStatus | None = None,
    priority: LeadPriority | None = None,
    manager_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    lead_source: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    sort: str = Query("newest", pattern="^(newest|oldest|priority|budget)$"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_VIEW)),
):
    leads, total = await lead_service.list_leads(
        db,
        current_user,
        page=page,
        size=size,
        search=search,
        status=status,
        priority=priority,
        manager_id=manager_id,
        project_id=project_id,
        lead_source=lead_source,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    pages = (total + size - 1) // size
    return LeadListResponse(items=leads, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=LeadRead, status_code=201)
async def create_lead(
    data: LeadCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_CREATE)),
):
    return await lead_service.create_lead(db, current_user, data)


@router.get("/{lead_id}", response_model=LeadRead)
async def get_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_VIEW)),
):
    return await lead_service.get_lead(db, current_user, lead_id)


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: uuid.UUID,
    data: LeadUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_UPDATE)),
):
    return await lead_service.update_lead(db, current_user, lead_id, data)


@router.delete("/{lead_id}", response_model=MessageResponse)
async def delete_lead(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_DELETE)),
):
    await lead_service.delete_lead(db, current_user, lead_id)
    return MessageResponse(message="Lead deleted successfully")


@router.patch("/{lead_id}/status", response_model=LeadRead)
async def move_lead_status(
    lead_id: uuid.UUID,
    data: LeadMoveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_MOVE)),
):
    return await lead_service.move_lead_status(db, current_user, lead_id, data)


@router.patch("/{lead_id}/manager", response_model=LeadRead)
async def assign_manager(
    lead_id: uuid.UUID,
    data: LeadAssignManagerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_ASSIGN)),
):
    return await lead_service.assign_manager(db, current_user, lead_id, data)


@router.get("/{lead_id}/notes", response_model=list[LeadNoteRead])
async def list_notes(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_VIEW)),
):
    return await lead_service.list_notes(db, current_user, lead_id)


@router.post("/{lead_id}/notes", response_model=LeadNoteRead, status_code=201)
async def add_note(
    lead_id: uuid.UUID,
    data: LeadNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_NOTES)),
):
    return await lead_service.add_note(db, current_user, lead_id, data)


@router.patch("/notes/{note_id}", response_model=LeadNoteRead)
async def update_note(
    note_id: uuid.UUID,
    data: LeadNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_NOTES)),
):
    return await lead_service.update_note(db, current_user, note_id, data)


@router.delete("/notes/{note_id}", response_model=MessageResponse)
async def delete_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_NOTES)),
):
    await lead_service.delete_note(db, current_user, note_id)
    return MessageResponse(message="Note deleted successfully")


@router.get("/{lead_id}/timeline", response_model=list[LeadTimelineRead])
async def list_timeline(
    lead_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission(LEADS_VIEW)),
):
    return await lead_service.list_timeline(db, current_user, lead_id)
