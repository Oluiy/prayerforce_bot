"""Database access for love letters and their deliveries."""
from database.prisma_connect import db


async def create(body, week_key):
    return await db.loveletter.create(data={"body": body, "weekKey": week_key})


async def get(letter_id):
    return await db.loveletter.find_unique(where={"id": letter_id})


async def list_for_week(week_key, active_only=True):
    """This week's letters, oldest first."""
    where = {"weekKey": week_key}
    if active_only:
        where["isActive"] = True
    return await db.loveletter.find_many(where=where, order={"createdAt": "asc"})


async def count_for_week(week_key):
    return await db.loveletter.count(where={"weekKey": week_key, "isActive": True})


async def deactivate(letter_id):
    return await db.loveletter.update(where={"id": letter_id}, data={"isActive": False})


async def delivered_user_ids(week_key, kind="weekly"):
    """Ids of members who already received a letter of this kind this week."""
    rows = await db.loveletterdelivery.find_many(
        where={"weekKey": week_key, "kind": kind}
    )
    return {row.userId for row in rows}


async def count_deliveries(week_key, kind="weekly"):
    return await db.loveletterdelivery.count(where={"weekKey": week_key, "kind": kind})


async def create_delivery(user_id, letter_id, kind, week_key, batch_id):
    return await db.loveletterdelivery.create(
        data={
            "userId": user_id,
            "letterId": letter_id,
            "kind": kind,
            "weekKey": week_key,
            "batchId": batch_id,
        }
    )
