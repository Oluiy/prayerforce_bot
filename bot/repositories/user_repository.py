"""Database access for users."""
from database.prisma_connect import db


async def get_by_chat_id(chat_id):
    return await db.user.find_unique(where={"chatId": str(chat_id)})


async def create(chat_id, first_name, last_name=None, birthday=None):
    data = {"chatId": str(chat_id), "firstName": first_name, "lastName": last_name}
    if birthday is not None:
        data["birthday"] = birthday
    return await db.user.create(data=data)


async def get_or_create(telegram_user):
    """Return the stored user for a Telegram user, creating it on first contact."""
    user = await get_by_chat_id(telegram_user.id)
    if user:
        return user
    return await create(telegram_user.id, telegram_user.first_name, telegram_user.last_name)


async def list_all():
    return await db.user.find_many()


async def list_by_birthday(day):
    """Users whose birthday falls on this month and day, in any year."""
    users = await db.user.find_many(where={"birthday": {"not": None}})
    return [u for u in users if (u.birthday.month, u.birthday.day) == (day.month, day.day)]


MEMBER_SEARCH_LIMIT = 10


def _name_matches(term: str):
    return {
        "OR": [
            {"firstName": {"contains": term, "mode": "insensitive"}},
            {"lastName": {"contains": term, "mode": "insensitive"}},
        ]
    }


async def search_by_name(term: str, limit: int = MEMBER_SEARCH_LIMIT):
    """Members whose first or last name contains `term`, case-insensitively."""
    return await db.user.find_many(
        where=_name_matches(term), take=limit, order={"firstName": "asc"}
    )


async def count_by_name(term: str) -> int:
    """How many members match, including any beyond the page we show."""
    return await db.user.count(where=_name_matches(term))


async def get_many_by_chat_ids(chat_ids):
    return await db.user.find_many(where={"chatId": {"in": [str(c) for c in chat_ids]}})
