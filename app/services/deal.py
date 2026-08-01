from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequest, Conflict, Forbidden, NotFound
from app.models.deal import (
    ACTIVE_STATUSES,
    PRE_RESERVATION_STATUSES,
    SELLABLE_STATUSES,
    STATUS_TRANSITIONS,
    Deal,
    DealPaymentType,
    DealPriority,
    DealStatus,
)
from app.models.deal_timeline import DealEvent
from app.models.matrix import Apartment
from app.models.user import User, UserRole
from app.repositories.deal import deal_repo
from app.repositories.deal_activity import deal_activity_repo
from app.repositories.deal_payment import deal_payment_repo
from app.repositories.deal_references import deal_reference_repo
from app.repositories.matrix import apartment_repo
from app.schemas.deal import (
    DealCancelRequest,
    DealCloseRequest,
    DealCreate,
    DealReserveRequest,
    DealUpdate,
)
from app.schemas.deal_payment import DealPaymentCreate
from app.services.deal_reservation import reservation_service
from app.services.deal_timeline import timeline_service

RESERVATION_DURATION_DAYS: int = 7
RESERVATION_WARNING_HOURS: int = 48
DEFAULT_CURRENCY: str = "USD"
SORT_OPTIONS: frozenset[str] = frozenset({"newest", "oldest", "price", "remaining", "created", "updated"})


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def validate_apartment_not_sold(db: AsyncSession, apartment: Apartment) -> None:
    if apartment.status.value == "sold":
        raise Conflict(f"Apartment {apartment.number} is already sold and cannot be reserved")


async def validate_apartment_not_blocked(db: AsyncSession, apartment: Apartment) -> None:
    if apartment.status.value == "blocked":
        raise Conflict(f"Apartment {apartment.number} is blocked and cannot be sold")


async def validate_no_duplicate_active_deal(
    db: AsyncSession, apartment_id: uuid.UUID, *, exclude_deal_id: uuid.UUID | None = None
) -> None:
    active = await deal_repo.get_active_by_apartment(db, apartment_id)
    if active and active.id != exclude_deal_id:
        raise Conflict("Another active deal already exists for this apartment")


async def validate_reservable_deal_status(deal: Deal) -> None:
    if deal.status in (DealStatus.SOLD, DealStatus.CANCELLED):
        raise BadRequest(f"Cannot reserve a deal in '{deal.status.value}' status")
    if deal.status not in PRE_RESERVATION_STATUSES:
        raise BadRequest(f"Deal is already in '{deal.status.value}' status; only pre-reservation statuses can reserve")


async def validate_sellable_deal_status(deal: Deal) -> None:
    if deal.status == DealStatus.SOLD:
        raise BadRequest("Deal is already sold")
    if deal.status == DealStatus.CANCELLED:
        raise BadRequest("Cancelled deal cannot be closed; restore it first")
    if deal.status not in SELLABLE_STATUSES:
        raise BadRequest(
            f"Deal cannot be closed from '{deal.status.value}' status; it must be reserved or have a contract first"
        )


async def validate_deal_not_final(deal: Deal, action: str = "modify") -> None:
    if deal.status == DealStatus.SOLD:
        raise BadRequest(f"Cannot {action} a sold deal")


async def validate_deal_has_apartment(deal: Deal) -> None:
    if deal.apartment_id is None:
        raise BadRequest("Deal has no apartment assigned")


async def validate_price_and_discount(price: float, discount: float) -> None:
    if price < 0:
        raise BadRequest("Price cannot be negative")
    if discount < 0:
        raise BadRequest("Discount cannot be negative")
    if discount > price:
        raise BadRequest("Discount cannot exceed the price")


async def validate_payment_amount(deal: Deal, amount: float) -> None:
    if amount <= 0:
        raise BadRequest("Payment amount must be positive")
    remaining = deal.final_price - deal.paid_amount
    if remaining <= 0:
        raise BadRequest("Deal is already fully paid")
    if amount > remaining:
        raise BadRequest(f"Payment amount exceeds the remaining balance of {remaining:.2f}")


def is_active_status(status: DealStatus) -> bool:
    return status in ACTIVE_STATUSES


class DealService:
    async def create_deal(self, db: AsyncSession, actor: User, data: DealCreate) -> Deal:
        create_data = data.model_dump()

        if actor.role == UserRole.MANAGER:
            create_data["manager_id"] = actor.id
        elif create_data.get("manager_id"):
            manager = await deal_reference_repo.get_manager(db, create_data["manager_id"])
            if not manager:
                raise NotFound("Manager not found or is not a manager")

        apartment = await self._validate_links(db, create_data)

        if apartment is not None:
            await validate_apartment_not_sold(db, apartment)
            await validate_apartment_not_blocked(db, apartment)
            await validate_no_duplicate_active_deal(db, apartment.id)

        price = create_data.get("price")
        if price is None:
            if apartment is not None:
                price = apartment.price
            else:
                raise BadRequest("price is required when no apartment is selected")

        discount = create_data.get("discount") or 0.0
        await validate_price_and_discount(price, discount)
        final_price = round(price - discount, 2)

        create_data["price"] = price
        create_data["discount"] = discount
        create_data["final_price"] = final_price
        create_data["paid_amount"] = 0.0
        create_data["remaining_amount"] = final_price
        create_data["currency"] = create_data.get("currency") or (apartment.currency if apartment else DEFAULT_CURRENCY)
        create_data["deal_number"] = self._generate_deal_number()
        create_data["created_by"] = actor.id
        create_data["updated_by"] = actor.id

        try:
            deal = await deal_repo.create(db, create_data)
        except IntegrityError as exc:
            raise Conflict("Another active deal already exists for this apartment") from exc

        if deal.lead_id:
            timeline_service.record(
                db, deal.id, DealEvent.LEAD_CONVERTED, new_value=str(deal.lead_id), performed_by=actor.id
            )
        timeline_service.record(
            db,
            deal.id,
            DealEvent.DEAL_CREATED,
            new_value=f"{deal.final_price:.2f} {deal.currency}",
            performed_by=actor.id,
        )
        return await self._get_deal_or_404(db, deal.id)

    async def get_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        if deal.status == DealStatus.RESERVED and deal.reservation_until and deal.reservation_until < _now():
            await self._expire_reservation(db, deal)
        self._ensure_access(actor, deal, write=False)
        return deal

    async def get_deal_for_read(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=False)
        return deal

    async def get_deal_for_write(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        return deal

    async def list_deals(
        self,
        db: AsyncSession,
        actor: User,
        *,
        page: int = 1,
        size: int = 20,
        search: str | None = None,
        status: DealStatus | None = None,
        priority: DealPriority | None = None,
        manager_id: uuid.UUID | None = None,
        project_id: uuid.UUID | None = None,
        building_id: uuid.UUID | None = None,
        apartment_id: uuid.UUID | None = None,
        payment_type: DealPaymentType | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        sort: str = "newest",
    ) -> tuple[list[Deal], int]:
        if sort not in SORT_OPTIONS:
            raise BadRequest(f"Invalid sort option. Choose from: {', '.join(sorted(SORT_OPTIONS))}")
        await self.expire_overdue_reservations(db)
        skip = (page - 1) * size
        scope_manager_id = actor.id if actor.role == UserRole.MANAGER else None
        scope_client_id = actor.id if actor.role == UserRole.CLIENT else None
        return await deal_repo.list(
            db,
            skip=skip,
            limit=size,
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
            scope_manager_id=scope_manager_id,
            scope_client_id=scope_client_id,
        )

    async def update_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealUpdate) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        await validate_deal_not_final(deal)

        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return deal

        if actor.role == UserRole.MANAGER and "manager_id" in update_data and update_data.get("manager_id") != actor.id:
            raise Forbidden("Managers cannot reassign deals to other managers")

        await self.expire_overdue_reservations(db)

        new_status = update_data.pop("status", None)
        if new_status is not None:
            await self._apply_status_change(
                db, deal, new_status, actor, contract_number=update_data.get("contract_number")
            )

        if any(
            key in update_data
            for key in (
                "client_id",
                "manager_id",
                "lead_id",
                "project_id",
                "building_id",
                "section_id",
                "floor_id",
                "apartment_id",
            )
        ):
            await self._validate_links(db, update_data)
            if "apartment_id" in update_data and update_data["apartment_id"] != deal.apartment_id:
                await self._validate_apartment_change(db, deal, update_data["apartment_id"])
                timeline_service.record(
                    db,
                    deal.id,
                    DealEvent.APARTMENT_CHANGED,
                    old_value=str(deal.apartment_id) if deal.apartment_id else None,
                    new_value=str(update_data["apartment_id"]) if update_data["apartment_id"] else None,
                    performed_by=actor.id,
                )

        if "price" in update_data or "discount" in update_data:
            new_price = update_data.get("price", deal.price)
            new_discount = update_data.get("discount", deal.discount)
            await validate_price_and_discount(new_price, new_discount)
            old_final = deal.final_price
            final_price = round(new_price - new_discount, 2)
            update_data["final_price"] = final_price
            update_data["remaining_amount"] = round(final_price - deal.paid_amount, 2)
            if final_price != old_final:
                timeline_service.record(
                    db,
                    deal.id,
                    DealEvent.DISCOUNT_UPDATED,
                    old_value=f"{old_final:.2f}",
                    new_value=f"{final_price:.2f}",
                    performed_by=actor.id,
                )

        if "manager_id" in update_data and update_data["manager_id"] != deal.manager_id:
            timeline_service.record(
                db,
                deal.id,
                DealEvent.MANAGER_CHANGED,
                old_value=str(deal.manager_id) if deal.manager_id else None,
                new_value=str(update_data["manager_id"]) if update_data["manager_id"] else None,
                performed_by=actor.id,
            )

        update_data["updated_by"] = actor.id
        try:
            updated = await deal_repo.update(db, deal, update_data)
        except IntegrityError as exc:
            raise Conflict("Another active deal already exists for this apartment") from exc

        timeline_service.record(db, deal.id, DealEvent.DEAL_UPDATED, performed_by=actor.id)
        return await self._get_deal_or_404(db, updated.id)

    async def delete_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> None:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)

        if deal.apartment_id:
            apartment = await self._get_apartment_or_404(db, deal.apartment_id)
            if apartment.deal_id == deal.id and deal.status != DealStatus.SOLD:
                await reservation_service.release(db, apartment)

        await deal_repo.soft_delete(db, deal)
        timeline_service.record(db, deal.id, DealEvent.DEAL_DELETED, performed_by=actor.id)

    async def reserve_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealReserveRequest) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        await self.expire_overdue_reservations(db)
        await validate_deal_not_final(deal, "reserve")
        await validate_reservable_deal_status(deal)
        await validate_deal_has_apartment(deal)

        apartment_id = deal.apartment_id
        if apartment_id is None:
            raise BadRequest("Deal must have an apartment to reserve")
        apartment = await self._get_apartment_or_404(db, apartment_id)
        await validate_apartment_not_sold(db, apartment)
        await validate_apartment_not_blocked(db, apartment)
        if apartment.status.value == "reserved" and apartment.deal_id != deal.id:
            raise Conflict("Apartment is already reserved by another deal")
        await validate_no_duplicate_active_deal(db, apartment_id, exclude_deal_id=deal.id)

        reservation_until = data.reservation_until or _now() + timedelta(days=RESERVATION_DURATION_DAYS)
        if data.reservation_until and data.reservation_until <= _now():
            raise BadRequest("reservation_until must be in the future")

        old_status = deal.status
        await deal_repo.update(
            db,
            deal,
            {
                "status": DealStatus.RESERVED,
                "reservation_until": reservation_until,
                "reservation_expired": False,
                "updated_by": actor.id,
            },
        )
        await reservation_service.hold(db, apartment, deal.id)
        timeline_service.record(
            db,
            deal.id,
            DealEvent.RESERVATION,
            old_value=old_status.value,
            new_value=DealStatus.RESERVED.value,
            performed_by=actor.id,
        )
        return await self._get_deal_or_404(db, deal.id)

    async def cancel_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealCancelRequest) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        if deal.status == DealStatus.SOLD:
            raise BadRequest("Cannot cancel a sold deal")
        if deal.status == DealStatus.CANCELLED:
            raise BadRequest("Deal is already cancelled")

        if deal.apartment_id:
            apartment = await self._get_apartment_or_404(db, deal.apartment_id)
            if apartment.deal_id == deal.id:
                await reservation_service.release(db, apartment)

        old_status = deal.status
        await deal_repo.update(
            db,
            deal,
            {
                "status": DealStatus.CANCELLED,
                "cancel_reason": data.cancel_reason,
                "reservation_expired": False,
                "updated_by": actor.id,
            },
        )
        timeline_service.record(
            db,
            deal.id,
            DealEvent.DEAL_CANCELLED,
            old_value=old_status.value,
            new_value=DealStatus.CANCELLED.value,
            performed_by=actor.id,
        )
        return await self._get_deal_or_404(db, deal.id)

    async def close_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealCloseRequest) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        await self.expire_overdue_reservations(db)
        await validate_sellable_deal_status(deal)
        await validate_deal_has_apartment(deal)

        apartment_id = deal.apartment_id
        if apartment_id is None:
            raise BadRequest("Deal must have an apartment to close")
        apartment = await self._get_apartment_or_404(db, apartment_id)
        await validate_apartment_not_blocked(db, apartment)
        if apartment.status.value == "sold" and apartment.deal_id != deal.id:
            raise Conflict("Apartment is already sold by another deal")

        contract_number = data.contract_number or deal.contract_number or self._generate_contract_number()
        old_status = deal.status
        await deal_repo.update(
            db,
            deal,
            {
                "status": DealStatus.SOLD,
                "closed_at": _now(),
                "contract_number": contract_number,
                "reservation_expired": False,
                "updated_by": actor.id,
            },
        )
        await reservation_service.mark_sold(db, apartment, deal.id)
        timeline_service.record(
            db,
            deal.id,
            DealEvent.DEAL_CLOSED,
            old_value=old_status.value,
            new_value=DealStatus.SOLD.value,
            performed_by=actor.id,
        )
        return await self._get_deal_or_404(db, deal.id)

    async def restore_deal(self, db: AsyncSession, actor: User, deal_id: uuid.UUID) -> Deal:
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        if deal.status != DealStatus.CANCELLED:
            raise BadRequest("Only cancelled deals can be restored")

        old_status = deal.status
        await deal_repo.update(
            db,
            deal,
            {
                "status": DealStatus.NEW,
                "cancel_reason": None,
                "reservation_expired": False,
                "reservation_until": None,
                "updated_by": actor.id,
            },
        )
        timeline_service.record(
            db,
            deal.id,
            DealEvent.DEAL_RESTORED,
            old_value=old_status.value,
            new_value=DealStatus.NEW.value,
            performed_by=actor.id,
        )
        return await self._get_deal_or_404(db, deal.id)

    async def add_payment(self, db: AsyncSession, actor: User, deal_id: uuid.UUID, data: DealPaymentCreate):
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=True)
        if deal.status == DealStatus.SOLD:
            raise BadRequest("Cannot add a payment to a sold deal")
        if deal.status == DealStatus.CANCELLED:
            raise BadRequest("Cannot add a payment to a cancelled deal")
        await validate_payment_amount(deal, data.amount)

        payment = await deal_payment_repo.create(
            db,
            {
                "deal_id": deal.id,
                "amount": data.amount,
                "payment_method": data.payment_method,
                "paid_at": data.paid_at or _now(),
                "note": data.note,
                "created_by": actor.id,
            },
        )
        old_paid = deal.paid_amount
        new_paid = round(old_paid + data.amount, 2)
        await deal_repo.update(
            db,
            deal,
            {
                "paid_amount": new_paid,
                "remaining_amount": round(deal.final_price - new_paid, 2),
                "updated_by": actor.id,
            },
        )
        timeline_service.record(
            db,
            deal.id,
            DealEvent.PAYMENT_ADDED,
            old_value=f"{old_paid:.2f}",
            new_value=f"{new_paid:.2f}",
            performed_by=actor.id,
        )
        return payment

    async def list_payments(self, db: AsyncSession, actor: User, deal_id: uuid.UUID):
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=False)
        return await deal_payment_repo.list_by_deal(db, deal_id)

    async def list_activities(self, db: AsyncSession, actor: User, deal_id: uuid.UUID):
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=False)
        return await deal_activity_repo.list_by_deal(db, deal_id, is_public_only=actor.role == UserRole.CLIENT)

    async def list_timeline(self, db: AsyncSession, actor: User, deal_id: uuid.UUID):
        deal = await self._get_deal_or_404(db, deal_id)
        self._ensure_access(actor, deal, write=False)
        return await timeline_service.list_for_deal(db, deal_id)

    async def _validate_apartment_change(self, db: AsyncSession, deal: Deal, apartment_id: uuid.UUID | None) -> None:
        if deal.status in (DealStatus.RESERVED, DealStatus.CONTRACT, DealStatus.INSTALLMENT, DealStatus.MORTGAGE):
            raise BadRequest("Cannot change the apartment while the deal has an active reservation or contract")
        if apartment_id is None:
            return
        apartment = await self._get_apartment_or_404(db, apartment_id)
        await validate_apartment_not_sold(db, apartment)
        await validate_apartment_not_blocked(db, apartment)
        await validate_no_duplicate_active_deal(db, apartment_id, exclude_deal_id=deal.id)

    async def _apply_status_change(
        self,
        db: AsyncSession,
        deal: Deal,
        new_status: DealStatus,
        actor: User,
        *,
        contract_number: str | None = None,
    ) -> None:
        if new_status == deal.status:
            return
        if deal.status == DealStatus.SOLD:
            raise BadRequest("Cannot change a sold deal")
        allowed = STATUS_TRANSITIONS.get(deal.status, set())
        if new_status not in allowed:
            raise BadRequest(f"Invalid status transition from '{deal.status.value}' to '{new_status.value}'")
        if new_status == DealStatus.RESERVED:
            raise BadRequest("Use the reserve endpoint to reserve a deal")
        if new_status == DealStatus.SOLD:
            raise BadRequest("Use the close endpoint to close a deal")
        if new_status == DealStatus.CANCELLED:
            raise BadRequest("Use the cancel endpoint to cancel a deal")

        old_status = deal.status
        updates: dict[str, object] = {"status": new_status, "updated_by": actor.id}
        if new_status == DealStatus.CONTRACT:
            generated = contract_number or deal.contract_number or self._generate_contract_number()
            updates["contract_number"] = generated
            await deal_repo.update(db, deal, updates)
            timeline_service.record(db, deal.id, DealEvent.CONTRACT_CREATED, new_value=generated, performed_by=actor.id)
        else:
            await deal_repo.update(db, deal, updates)
        timeline_service.record(
            db,
            deal.id,
            DealEvent.STATUS_CHANGED,
            old_value=old_status.value,
            new_value=new_status.value,
            performed_by=actor.id,
        )

    async def _expire_reservation(self, db: AsyncSession, deal: Deal, actor_id: uuid.UUID | None = None) -> None:
        if deal.apartment_id and deal.apartment and deal.apartment.deal_id == deal.id:
            await reservation_service.release(db, deal.apartment)
        old_until = deal.reservation_until.isoformat() if deal.reservation_until else None
        deal.reservation_expired = True
        deal.updated_by = actor_id
        await db.flush()
        timeline_service.record(
            db,
            deal.id,
            DealEvent.RESERVATION_EXPIRED,
            old_value=old_until,
            new_value="expired",
            performed_by=actor_id,
        )

    async def expire_overdue_reservations(self, db: AsyncSession) -> None:
        overdue = await deal_repo.list_overdue_reservations(db, _now())
        for deal in overdue:
            await self._expire_reservation(db, deal)

    async def _validate_links(self, db: AsyncSession, data: dict) -> Apartment | None:
        client_id = data.get("client_id")
        manager_id = data.get("manager_id")
        lead_id = data.get("lead_id")
        project_id = data.get("project_id")
        building_id = data.get("building_id")
        section_id = data.get("section_id")
        floor_id = data.get("floor_id")
        apartment_id = data.get("apartment_id")

        if client_id is not None:
            client = await deal_reference_repo.get_client(db, client_id)
            if not client:
                raise NotFound("Client not found or is not a client")
        if manager_id is not None:
            manager = await deal_reference_repo.get_manager(db, manager_id)
            if not manager:
                raise NotFound("Manager not found or is not a manager")
        if lead_id is not None:
            lead = await deal_reference_repo.get_lead(db, lead_id)
            if not lead:
                raise NotFound("Lead not found")

        if project_id is not None and not await deal_reference_repo.get_project(db, project_id):
            raise NotFound("Project not found")

        building = None
        if building_id is not None:
            building = await deal_reference_repo.get_building(db, building_id)
            if not building:
                raise NotFound("Building not found")
            if project_id is not None and building.project_id != project_id:
                raise BadRequest("Building does not belong to the given project")

        if section_id is not None:
            section = await deal_reference_repo.get_section(db, section_id)
            if not section:
                raise NotFound("Section not found")
            if building_id is not None and section.building_id != building_id:
                raise BadRequest("Section does not belong to the given building")

        if floor_id is not None:
            floor = await deal_reference_repo.get_floor(db, floor_id)
            if not floor:
                raise NotFound("Floor not found")
            if building_id is not None and floor.building_id != building_id:
                raise BadRequest("Floor does not belong to the given building")

        apartment = None
        if apartment_id is not None:
            apartment = await apartment_repo.get_by_id_with_floor(db, apartment_id)
            if not apartment:
                raise NotFound("Apartment not found")
            if floor_id is not None and apartment.floor_id != floor_id:
                raise BadRequest("Apartment does not belong to the given floor")
            if building_id is not None and apartment.floor.building_id != building_id:
                raise BadRequest("Apartment does not belong to the given building")
        return apartment

    async def _get_deal_or_404(self, db: AsyncSession, deal_id: uuid.UUID) -> Deal:
        deal = await deal_repo.get_by_id(db, deal_id)
        if not deal:
            raise NotFound("Deal not found")
        return deal

    async def _get_apartment_or_404(self, db: AsyncSession, apartment_id: uuid.UUID) -> Apartment:
        apartment = await apartment_repo.get_by_id_with_floor(db, apartment_id)
        if not apartment:
            raise NotFound("Apartment not found")
        return apartment

    @staticmethod
    def _ensure_access(actor: User, deal: Deal, *, write: bool) -> None:
        if actor.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return
        if actor.role == UserRole.MANAGER:
            if deal.manager_id != actor.id:
                raise Forbidden("You can only access your own deals")
            return
        if actor.role == UserRole.CLIENT:
            if deal.client_id != actor.id:
                raise Forbidden("You can only access your own deals")
            if write:
                raise Forbidden("Clients have read-only access to their deals")
            return

    @staticmethod
    def _generate_contract_number() -> str:
        return f"CNTR-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"

    @staticmethod
    def _generate_deal_number() -> str:
        return f"DL-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"


deal_service = DealService()
