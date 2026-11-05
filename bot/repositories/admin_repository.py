"""Database access for temporary admin grants."""
from database.prisma_connect import db


async def list_active(now):
    """Grants that haven't been revoked and haven't run out yet."""
    return await db.admingrant.find_many(
        where={"revokedAt": None, "expiresAt": {"gt": now}},
        order={"expiresAt": "asc"},
    )


async def find_active_for(telegram_id, now):
    return await db.admingrant.find_first(
        where={"telegramId": str(telegram_id), "revokedAt": None, "expiresAt": {"gt": now}}
    )


async def create(telegram_id, expires_at, granted_by):
    return await db.admingrant.create(
        data={
            "telegramId": str(telegram_id),
            "expiresAt": expires_at,
            "grantedBy": str(granted_by),
        }
    )


async def revoke_for(telegram_id, revoked_by, now):
    """End any live grant for this member. Returns how many were ended."""
    result = await db.admingrant.update_many(
        where={"telegramId": str(telegram_id), "revokedAt": None, "expiresAt": {"gt": now}},
        data={"revokedAt": now, "revokedBy": str(revoked_by)},
    )
    return result
