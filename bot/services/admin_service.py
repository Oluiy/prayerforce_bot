"""Who counts as an admin.

Permanent admins come from ADMIN_IDS in .env. Temporary admins are grants
stored in the database with an expiry.

Active grants are held in memory so `is_admin` stays a plain function and
every existing caller keeps working. The cache is refreshed when a grant
changes and when grants expire.
"""
import datetime
import logging

from config import settings
from repositories import admin_repository
from utils.dates import utc_now

logger = logging.getLogger(__name__)

MIN_DURATION = datetime.timedelta(minutes=1)
MAX_DURATION = datetime.timedelta(days=30)

# telegram id -> when their grant runs out
_temporary: dict[int, datetime.datetime] = {}


class AdminError(Exception):
    """Raised when a grant can't be made, with a message safe to show an admin."""


def permanent_admin_ids() -> tuple[int, ...]:
    return settings.admin_ids


def is_permanent_admin(user_id) -> bool:
    return int(user_id) in settings.admin_ids


def is_admin(user_id) -> bool:
    """True for permanent admins and for members with a grant still running."""
    user_id = int(user_id)
    if user_id in settings.admin_ids:
        return True
    expires_at = _temporary.get(user_id)
    return expires_at is not None and expires_at > utc_now()


def expires_at(user_id) -> datetime.datetime | None:
    """When this member's temporary access ends, or None if they aren't temporary."""
    return _temporary.get(int(user_id))


def temporary_ids() -> list[int]:
    now = utc_now()
    return [user_id for user_id, until in _temporary.items() if until > now]


async def load():
    """Read live grants into the cache. Called at startup."""
    global _temporary
    try:
        grants = await admin_repository.list_active(utc_now())
    except Exception as e:
        # Never let this stop the bot; permanent admins still work.
        logger.warning("Could not load admin grants: %s", e)
        _temporary = {}
        return _temporary

    _temporary = {int(g.telegramId): g.expiresAt for g in grants}
    if _temporary:
        logger.info("Loaded %s temporary admin(s).", len(_temporary))
    return _temporary


async def grant(telegram_id, duration: datetime.timedelta, granted_by) -> datetime.datetime:
    """Give a member admin rights for `duration`. Returns when it runs out.

    Re-granting to the same member replaces their current grant.
    """
    telegram_id = int(telegram_id)

    if is_permanent_admin(telegram_id):
        raise AdminError("They're already a permanent admin, so there's nothing to grant.")
    if duration < MIN_DURATION:
        raise AdminError("That's too short. Use at least 1 minute.")
    if duration > MAX_DURATION:
        raise AdminError("That's too long. Use 30 days or less.")

    now = utc_now()
    # Replace any grant they already have, so the clock restarts cleanly.
    await admin_repository.revoke_for(telegram_id, revoked_by=granted_by, now=now)
    expiry = now + duration
    await admin_repository.create(telegram_id, expiry, granted_by)
    _temporary[telegram_id] = expiry
    logger.info("Granted temporary admin to %s until %s (by %s)", telegram_id, expiry, granted_by)
    return expiry


async def revoke(telegram_id, revoked_by) -> bool:
    """End a member's temporary access now. False if they had none."""
    telegram_id = int(telegram_id)
    if is_permanent_admin(telegram_id):
        raise AdminError("They're a permanent admin — remove them from ADMIN_IDS in .env instead.")

    had_grant = telegram_id in _temporary
    await admin_repository.revoke_for(telegram_id, revoked_by=revoked_by, now=utc_now())
    _temporary.pop(telegram_id, None)
    if had_grant:
        logger.info("Revoked temporary admin for %s (by %s)", telegram_id, revoked_by)
    return had_grant


def expire_due(now=None) -> list[int]:
    """Drop grants that have run out. Returns whose access just ended."""
    now = now or utc_now()
    expired = [user_id for user_id, until in _temporary.items() if until <= now]
    for user_id in expired:
        del _temporary[user_id]
    if expired:
        logger.info("Temporary admin ended for %s", expired)
    return expired
