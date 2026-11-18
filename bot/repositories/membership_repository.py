"""Database access for who belongs to which session (e.g. 2025/2026).

A person has one User row for life and one Membership row per session they
were part of, so history is kept without duplicating anyone.
"""
from database.prisma_connect import db


def _key(user_id: str, session: str):
    return {"userId_session": {"userId": user_id, "session": session}}


async def get(user_id: str, session: str):
    return await db.membership.find_unique(where=_key(user_id, session))


async def set_active(user_id: str, session: str, active: bool):
    """Record whether someone is part of a session, creating the row if needed."""
    return await db.membership.upsert(
        where=_key(user_id, session),
        data={
            "create": {"userId": user_id, "session": session, "active": active},
            "update": {"active": active},
        },
    )


async def enroll_many(user_ids, session: str) -> int:
    """Add several people to a session at once. Anyone already in it is left alone."""
    if not user_ids:
        return 0
    return await db.membership.create_many(
        data=[{"userId": user_id, "session": session} for user_id in user_ids],
        skip_duplicates=True,
    )


async def count_active(session: str) -> int:
    return await db.membership.count(where={"session": session, "active": True})


async def has_any() -> bool:
    return await db.membership.count() > 0
