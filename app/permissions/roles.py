from app.core.exceptions import Forbidden
from app.models.user import User, UserRole

USERS_CREATE = "users.create"
USERS_UPDATE = "users.update"
USERS_DELETE = "users.delete"
USERS_CHANGE_ROLE = "users.change_role"
USERS_VIEW = "users.view"
USERS_RESET_PASSWORD = "users.reset_password"

MATRIX_CREATE = "matrix.create"
MATRIX_UPDATE = "matrix.update"
MATRIX_VIEW = "matrix.view"
MATRIX_RESERVE = "matrix.reserve"
MATRIX_DELETE = "matrix.delete"

LEADS_CREATE = "leads.create"
LEADS_VIEW = "leads.view"
LEADS_UPDATE = "leads.update"
LEADS_DELETE = "leads.delete"
LEADS_MOVE = "leads.move"
LEADS_ASSIGN = "leads.assign"
LEADS_NOTES = "leads.notes"

DEALS_CREATE = "deals.create"
DEALS_VIEW = "deals.view"
DEALS_UPDATE = "deals.update"
DEALS_DELETE = "deals.delete"
DEALS_RESERVE = "deals.reserve"
DEALS_CANCEL = "deals.cancel"
DEALS_CLOSE = "deals.close"
DEALS_RESTORE = "deals.restore"
DEALS_TIMELINE = "deals.timeline"
DEALS_ACTIVITIES = "deals.activities"
DEALS_TASKS = "deals.tasks"
DEALS_DOCUMENTS = "deals.documents"
DEALS_PAYMENTS = "deals.payments"
DEALS_STATISTICS = "deals.statistics"
DEALS_DASHBOARD = "deals.dashboard"

DEAL_PERMISSIONS: frozenset[str] = frozenset(
    {
        DEALS_CREATE,
        DEALS_VIEW,
        DEALS_UPDATE,
        DEALS_DELETE,
        DEALS_RESERVE,
        DEALS_CANCEL,
        DEALS_CLOSE,
        DEALS_RESTORE,
        DEALS_TIMELINE,
        DEALS_ACTIVITIES,
        DEALS_TASKS,
        DEALS_DOCUMENTS,
        DEALS_PAYMENTS,
        DEALS_STATISTICS,
        DEALS_DASHBOARD,
    }
)

MANAGER_DEAL_PERMISSIONS: frozenset[str] = frozenset(
    {
        DEALS_CREATE,
        DEALS_VIEW,
        DEALS_UPDATE,
        DEALS_RESERVE,
        DEALS_CANCEL,
        DEALS_CLOSE,
        DEALS_RESTORE,
        DEALS_TIMELINE,
        DEALS_ACTIVITIES,
        DEALS_TASKS,
        DEALS_DOCUMENTS,
        DEALS_PAYMENTS,
        DEALS_STATISTICS,
        DEALS_DASHBOARD,
    }
)

ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.SUPER_ADMIN: {
        USERS_CREATE,
        USERS_UPDATE,
        USERS_DELETE,
        USERS_CHANGE_ROLE,
        USERS_VIEW,
        USERS_RESET_PASSWORD,
        MATRIX_CREATE,
        MATRIX_UPDATE,
        MATRIX_VIEW,
        MATRIX_RESERVE,
        MATRIX_DELETE,
        LEADS_CREATE,
        LEADS_VIEW,
        LEADS_UPDATE,
        LEADS_DELETE,
        LEADS_MOVE,
        LEADS_ASSIGN,
        LEADS_NOTES,
        *DEAL_PERMISSIONS,
    },
    UserRole.ADMIN: {
        USERS_CREATE,
        USERS_UPDATE,
        USERS_DELETE,
        USERS_CHANGE_ROLE,
        USERS_VIEW,
        USERS_RESET_PASSWORD,
        MATRIX_CREATE,
        MATRIX_UPDATE,
        MATRIX_VIEW,
        MATRIX_RESERVE,
        MATRIX_DELETE,
        LEADS_CREATE,
        LEADS_VIEW,
        LEADS_UPDATE,
        LEADS_DELETE,
        LEADS_MOVE,
        LEADS_ASSIGN,
        LEADS_NOTES,
        *DEAL_PERMISSIONS,
    },
    UserRole.MANAGER: {
        USERS_VIEW,
        MATRIX_VIEW,
        MATRIX_RESERVE,
        LEADS_CREATE,
        LEADS_VIEW,
        LEADS_UPDATE,
        LEADS_MOVE,
        LEADS_NOTES,
        *MANAGER_DEAL_PERMISSIONS,
    },
    UserRole.CLIENT: set(),
}


def has_permission(actor: User, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(actor.role, set())


def require_permission(permission: str):
    def checker(actor: User) -> None:
        if not has_permission(actor, permission):
            raise Forbidden(f"Missing permission: {permission}")

    return checker


def require_target_not_super_admin(target: User) -> None:
    if target.role == UserRole.SUPER_ADMIN:
        raise Forbidden("Cannot modify a Super Admin")


def require_can_create_user(actor: User, target_role: UserRole) -> None:
    require_permission(USERS_CREATE)(actor)
    if actor.role == UserRole.ADMIN and target_role == UserRole.SUPER_ADMIN:
        raise Forbidden("Admin cannot create Super Admin users")


def require_can_manage_user(actor: User, target: User) -> None:
    require_permission(USERS_UPDATE)(actor)
    if actor.role == UserRole.ADMIN:
        require_target_not_super_admin(target)


def require_can_delete_user(actor: User, target: User) -> None:
    require_permission(USERS_DELETE)(actor)
    if actor.role == UserRole.ADMIN:
        require_target_not_super_admin(target)


def require_can_change_role(actor: User, target: User, new_role: UserRole) -> None:
    require_permission(USERS_CHANGE_ROLE)(actor)
    if actor.role == UserRole.ADMIN:
        require_target_not_super_admin(target)
        if new_role == UserRole.SUPER_ADMIN:
            raise Forbidden("Admin cannot change role to Super Admin")


def require_can_reset_password(actor: User, target: User) -> None:
    require_permission(USERS_RESET_PASSWORD)(actor)
    if actor.role == UserRole.ADMIN:
        require_target_not_super_admin(target)
