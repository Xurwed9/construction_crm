from app.core.exceptions import Forbidden
from app.models.user import User, UserRole


def check_can_create_user(actor: User, target_role: UserRole) -> None:
    if actor.role == UserRole.SUPER_ADMIN:
        return

    if actor.role == UserRole.ADMIN:
        if target_role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            raise Forbidden("Admin cannot create Super Admin or Admin users")
        return

    raise Forbidden("You do not have permission to create users")


def check_can_manage_user(actor: User, target: User) -> None:
    if actor.role == UserRole.SUPER_ADMIN:
        return

    if actor.role == UserRole.ADMIN:
        if target.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            raise Forbidden("Admin cannot manage Super Admin or Admin users")
        return

    raise Forbidden("You do not have permission to manage users")


def check_can_change_role(actor: User, target: User, new_role: UserRole) -> None:
    if actor.role == UserRole.SUPER_ADMIN:
        return

    if actor.role == UserRole.ADMIN:
        if target.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            raise Forbidden("Admin cannot change role for Super Admin or Admin users")
        if new_role in (UserRole.SUPER_ADMIN, UserRole.ADMIN):
            raise Forbidden("Admin cannot assign Super Admin or Admin roles")
        return

    raise Forbidden("You do not have permission to change roles")
