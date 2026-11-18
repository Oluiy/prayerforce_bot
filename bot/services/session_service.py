"""Which session (e.g. 2025/2026) is running, and who is part of it.

Anything the bot sends to "everyone" goes to the members of the current
session only, so people who graduated or left stop hearing from it while
their history stays in the database.
"""
import logging
import re

from config.constants import DEFAULT_SESSION
from repositories import membership_repository, setting_repository, user_repository

logger = logging.getLogger(__name__)

# Stored in the Setting table but changed through /new_session, not /settings,
# because changing it also has to invite members into the new session.
SESSION_KEY = "current_session"
SESSION_FORMAT = re.compile(r"^(\d{4})\s*/\s*(\d{4})$")

_current: str | None = None


class SessionError(ValueError):
    """Something an admin typed that can't be a session."""


def parse(raw: str) -> str:
    """Turn admin input like '2026/2027' into a session name, or raise SessionError."""
    found = SESSION_FORMAT.match((raw or "").strip())
    if not found:
        raise SessionError("Please send it as two years, like 2026/2027.")
    start, end = int(found.group(1)), int(found.group(2))
    if end != start + 1:
        raise SessionError("The second year should come right after the first, like 2026/2027.")
    return f"{start}/{end}"


def next_after(session: str) -> str:
    start = int(session.split("/")[0]) + 1
    return f"{start}/{start + 1}"


def current() -> str:
    return _current or DEFAULT_SESSION


async def load():
    """Read the current session at startup, and enroll existing users the first time."""
    global _current
    try:
        stored = await setting_repository.get_all()
        _current = stored.get(SESSION_KEY) or DEFAULT_SESSION
    except Exception as e:
        logger.warning("Could not load the current session, using %s: %s", DEFAULT_SESSION, e)
        _current = DEFAULT_SESSION
        return
    logger.info("Current session is %s.", _current)
    await _backfill_if_empty()


async def _backfill_if_empty():
    """Before sessions existed, everyone was a member. Keep it that way once.

    Only runs while the Membership table is completely empty, so it can't
    pull graduates back in after the first rollover.
    """
    try:
        if await membership_repository.has_any():
            return
        users = await user_repository.list_all()
        added = await membership_repository.enroll_many([u.id for u in users], current())
        logger.info("Enrolled %s existing user(s) into %s.", added, current())
    except Exception:
        logger.exception("Could not enroll existing users into %s", current())


async def members():
    """Active members of the current session."""
    return await user_repository.list_members(current())


async def member_count() -> int:
    return await membership_repository.count_active(current())


async def join(user):
    """Mark a stored user as part of the current session."""
    return await membership_repository.set_active(user.id, current(), True)


async def leave(user):
    """Record that a user is not part of the current session. Their history stays."""
    return await membership_repository.set_active(user.id, current(), False)


async def start_new(session: str, started_by: str | None = None):
    """Switch to a new session. Returns the previous session's members to invite."""
    global _current
    previous = current()
    previous_members = await user_repository.list_members(previous)
    await setting_repository.set(SESSION_KEY, session, updated_by=started_by)
    _current = session
    logger.info("Session changed from %s to %s by %s", previous, session, started_by)
    return previous, previous_members
