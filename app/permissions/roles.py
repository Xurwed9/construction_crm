from app.core.exceptions import Forbidden
from app.models.user import User, UserRole


def check_can_create_user(actor: User) -> None:
    if actor.role == UserRole.ADMIN:
        return
    raise Forbidden("Only Admin can create users")


def check_can_manage_user(actor: User) -> None:
    if actor.role == UserRole.ADMIN:
        return
    raise Forbidden("Only Admin can manage users")


def check_can_change_role(actor: User) -> None:
    if actor.role == UserRole.ADMIN:
        return
    raise Forbidden("Only Admin can change roles")
