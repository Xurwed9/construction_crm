import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequest, Forbidden, NotFound
from app.models.lead import (
    STATUS_TRANSITIONS,
    Lead,
    LeadNote,
    LeadPriority,
    LeadStatus,
    LeadTimeline,
)
from app.models.user import User, UserRole
from app.repositories.lead import (
    lead_note_repo,
    lead_reference_repo,
    lead_repo,
    lead_timeline_repo,
)
from app.repositories.matrix import apartment_repo, building_repo, project_repo
from app.schemas.lead import (
    LeadAssignManagerRequest,
    LeadCreate,
    LeadMoveRequest,
    LeadNoteCreate,
    LeadNoteUpdate,
    LeadUpdate,
)

SORT_OPTIONS = {"newest", "oldest", "priority", "budget"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LeadService:
    async def create_lead(self, db: AsyncSession, actor: User, data: LeadCreate) -> Lead:
        create_data = data.model_dump()

        if actor.role == UserRole.MANAGER:
            create_data["assigned_manager_id"] = actor.id
        elif create_data.get("assigned_manager_id"):
            manager = await lead_reference_repo.get_manager(db, create_data["assigned_manager_id"])
            if not manager:
                raise NotFound("Assigned manager not found or is not a manager")

        await self._validate_links(db, create_data)

        create_data["full_name"] = self._build_full_name(create_data["first_name"], create_data["last_name"])
        create_data["created_by"] = actor.id
        create_data["updated_by"] = actor.id
        create_data["last_activity_at"] = _now()

        lead = await lead_repo.create(db, create_data)
        await self._add_timeline(db, lead, "lead_created", f"Lead created for {lead.full_name}", actor.id)
        return lead

    async def get_lead(self, db: AsyncSession, actor: User, lead_id: uuid.UUID) -> Lead:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)
        return lead

    async def list_leads(
        self,
        db: AsyncSession,
        actor: User,
        *,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
        status: LeadStatus | None = None,
        priority: LeadPriority | None = None,
        manager_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        lead_source: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "newest",
    ) -> tuple[list[Lead], int]:
        if sort not in SORT_OPTIONS:
            raise BadRequest(f"Invalid sort option. Choose from: {', '.join(sorted(SORT_OPTIONS))}")
        skip = (page - 1) * size
        scope_manager_id = actor.id if actor.role == UserRole.MANAGER else None
        return await lead_repo.list(
            db,
            skip=skip,
            limit=size,
            search=search,
            status=status,
            priority=priority,
            manager_id=manager_id,
            project_id=project_id,
            lead_source=lead_source,
            date_from=date_from,
            date_to=date_to,
            sort=sort,
            scope_manager_id=scope_manager_id,
        )

    async def update_lead(self, db: AsyncSession, actor: User, lead_id: uuid.UUID, data: LeadUpdate) -> Lead:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return lead

        await self._validate_links(db, update_data)

        if "first_name" in update_data or "last_name" in update_data:
            first_name = update_data.get("first_name", lead.first_name)
            last_name = update_data.get("last_name", lead.last_name)
            update_data["full_name"] = self._build_full_name(first_name, last_name)

        update_data["updated_by"] = actor.id
        update_data["last_activity_at"] = _now()

        updated = await lead_repo.update(db, lead, update_data)
        await self._add_timeline(db, updated, "lead_updated", "Lead details updated", actor.id)
        return updated

    async def delete_lead(self, db: AsyncSession, actor: User, lead_id: uuid.UUID) -> None:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)
        await lead_repo.soft_delete(db, lead)
        await self._add_timeline(db, lead, "lead_deleted", "Lead deleted", actor.id)

    async def get_kanban(
        self,
        db: AsyncSession,
        actor: User,
        *,
        search: str | None = None,
        status: LeadStatus | None = None,
        priority: LeadPriority | None = None,
        manager_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        lead_source: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict[LeadStatus, list[Lead]]:
        scope_manager_id = actor.id if actor.role == UserRole.MANAGER else None
        return await lead_repo.kanban(
            db,
            search=search,
            status=status,
            priority=priority,
            manager_id=manager_id,
            project_id=project_id,
            lead_source=lead_source,
            date_from=date_from,
            date_to=date_to,
            scope_manager_id=scope_manager_id,
        )

    async def move_lead_status(self, db: AsyncSession, actor: User, lead_id: uuid.UUID, data: LeadMoveRequest) -> Lead:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)

        new_status = data.status
        if new_status == lead.status:
            return lead

        allowed = STATUS_TRANSITIONS.get(lead.status, set())
        if new_status not in allowed:
            raise BadRequest(f"Invalid status transition from '{lead.status.value}' to '{new_status.value}'")

        old_status = lead.status
        updated = await lead_repo.update(
            db, lead, {"status": new_status, "updated_by": actor.id, "last_activity_at": _now()}
        )
        await self._add_timeline(
            db,
            updated,
            "status_changed",
            f"Status changed from '{old_status.value}' to '{new_status.value}'",
            actor.id,
        )
        return updated

    async def assign_manager(
        self, db: AsyncSession, actor: User, lead_id: uuid.UUID, data: LeadAssignManagerRequest
    ) -> Lead:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)

        manager = await lead_reference_repo.get_manager(db, data.assigned_manager_id)
        if not manager:
            raise NotFound("Assigned manager not found or is not a manager")

        old_manager = lead.assigned_manager_id
        updated = await lead_repo.update(
            db, lead, {"assigned_manager_id": data.assigned_manager_id, "updated_by": actor.id}
        )
        description = f"Manager assigned: {manager.full_name}"
        if old_manager:
            description = f"Manager changed to {manager.full_name}"
        await self._add_timeline(db, updated, "manager_assigned", description, actor.id)
        return updated

    async def add_note(self, db: AsyncSession, actor: User, lead_id: uuid.UUID, data: LeadNoteCreate) -> LeadNote:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)

        note = await lead_note_repo.create(db, {"lead_id": lead_id, "author_id": actor.id, "content": data.content})
        lead.last_activity_at = _now()
        await self._add_timeline(db, lead, "note_added", "Note added", actor.id)
        return note

    async def update_note(self, db: AsyncSession, actor: User, note_id: uuid.UUID, data: LeadNoteUpdate) -> LeadNote:
        note = await self._get_note_or_404(db, note_id)
        lead = await self._get_lead_or_404(db, note.lead_id)
        self._ensure_lead_access(actor, lead)
        self._ensure_note_editable(actor, note)

        updated = await lead_note_repo.update(db, note, {"content": data.content})
        lead.last_activity_at = _now()
        await self._add_timeline(db, lead, "note_updated", "Note updated", actor.id)
        return updated

    async def delete_note(self, db: AsyncSession, actor: User, note_id: uuid.UUID) -> None:
        note = await self._get_note_or_404(db, note_id)
        lead = await self._get_lead_or_404(db, note.lead_id)
        self._ensure_lead_access(actor, lead)
        self._ensure_note_editable(actor, note)

        await lead_note_repo.delete(db, note)
        lead.last_activity_at = _now()
        await self._add_timeline(db, lead, "note_deleted", "Note deleted", actor.id)

    async def list_notes(self, db: AsyncSession, actor: User, lead_id: uuid.UUID) -> list[LeadNote]:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)
        return await lead_note_repo.list_by_lead(db, lead_id)

    async def list_timeline(self, db: AsyncSession, actor: User, lead_id: uuid.UUID) -> list[LeadTimeline]:
        lead = await self._get_lead_or_404(db, lead_id)
        self._ensure_lead_access(actor, lead)
        return await lead_timeline_repo.list_by_lead(db, lead_id)

    async def _get_lead_or_404(self, db: AsyncSession, lead_id: uuid.UUID) -> Lead:
        lead = await lead_repo.get_by_id(db, lead_id)
        if not lead:
            raise NotFound("Lead not found")
        return lead

    async def _get_note_or_404(self, db: AsyncSession, note_id: uuid.UUID) -> LeadNote:
        note = await lead_note_repo.get_by_id(db, note_id)
        if not note:
            raise NotFound("Note not found")
        return note

    async def _validate_links(self, db: AsyncSession, data: dict) -> None:
        project_id = data.get("project_id")
        building_id = data.get("building_id")
        apartment_id = data.get("apartment_id")

        if project_id and not await project_repo.get_by_id(db, project_id):
            raise NotFound("Project not found")

        if building_id:
            building = await building_repo.get_by_id(db, building_id)
            if not building:
                raise NotFound("Building not found")
            if project_id and building.project_id != project_id:
                raise BadRequest("Building does not belong to the given project")

        if apartment_id:
            apartment = await apartment_repo.get_by_id_with_floor(db, apartment_id)
            if not apartment:
                raise NotFound("Apartment not found")
            if building_id and apartment.floor.building_id != building_id:
                raise BadRequest("Apartment does not belong to the given building")

    async def _add_timeline(
        self, db: AsyncSession, lead: Lead, action: str, description: str, actor_id: uuid.UUID | None
    ) -> None:
        await lead_timeline_repo.create(
            db,
            {
                "lead_id": lead.id,
                "action": action,
                "description": description,
                "actor_id": actor_id,
            },
        )
        lead.last_activity_at = _now()

    @staticmethod
    def _build_full_name(first_name: str, last_name: str) -> str:
        return f"{first_name} {last_name}".strip()

    @staticmethod
    def _ensure_lead_access(actor: User, lead: Lead) -> None:
        if actor.role == UserRole.MANAGER and lead.assigned_manager_id != actor.id:
            raise Forbidden("You can only access your own leads")

    @staticmethod
    def _ensure_note_editable(actor: User, note: LeadNote) -> None:
        if actor.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN) and note.author_id != actor.id:
            raise Forbidden("You can only edit your own notes")


lead_service = LeadService()
