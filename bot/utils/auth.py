"""Who is allowed to do what.

Handlers import from here. Permanent admins come from ADMIN_IDS in .env;
temporary ones are time-limited grants held by services/admin_service.py.
"""
from config import settings
from services import admin_service


def is_admin(user) -> bool:
    """A permanent admin, or a member whose temporary access is still running."""
    return bool(user) and admin_service.is_admin(user.id)


def is_permanent_admin(user) -> bool:
    return bool(user) and admin_service.is_permanent_admin(user.id)


def is_primary_admin(user) -> bool:
    return bool(user) and settings.primary_admin_id is not None and user.id == settings.primary_admin_id


def can_manage_admins(user) -> bool:
    """Only permanent admins hand out or take back access.

    This stops a temporary admin from extending their own time or promoting
    someone else.
    """
    return is_permanent_admin(user)
