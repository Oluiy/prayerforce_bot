from config import settings


def is_admin(user) -> bool:
    return bool(user) and user.id in settings.admin_ids


def is_primary_admin(user) -> bool:
    return bool(user) and settings.primary_admin_id is not None and user.id == settings.primary_admin_id
