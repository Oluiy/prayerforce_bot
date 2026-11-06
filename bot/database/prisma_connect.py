"""Shared Prisma client. Connect once at startup (see main.py)."""
import asyncio
import logging
from datetime import timedelta

from config.constants import DATABASE_CONNECT_ATTEMPTS, DATABASE_CONNECT_TIMEOUT_SECONDS
from prisma import Prisma

logger = logging.getLogger(__name__)

# Prisma runs its query engine as a separate process and polls it until it
# answers. A cold start can take longer than the 10 second default, which
# surfaces as "Could not connect to the query engine" even though the
# database itself is fine.
db = Prisma(connect_timeout=timedelta(seconds=DATABASE_CONNECT_TIMEOUT_SECONDS))


async def connect_with_retry(attempts: int = DATABASE_CONNECT_ATTEMPTS):
    """Connect to the database, giving a slow query engine a few more chances."""
    for attempt in range(1, attempts + 1):
        try:
            await db.connect()
            return
        except Exception as e:
            if attempt == attempts:
                raise
            wait = 2 * attempt
            logger.warning(
                "Database connection attempt %s of %s failed (%s). Retrying in %ss...",
                attempt, attempts, e, wait,
            )
            await asyncio.sleep(wait)


# Every table the bot uses. If the generated client is missing one, the
# schema was changed without running `prisma generate`.
REQUIRED_MODELS = (
    "user",
    "quiz",
    "question",
    "option",
    "userscore",
    "dailyquizcumulative",
    "setting",
    "admingrant",
)


def missing_models() -> list[str]:
    return [name for name in REQUIRED_MODELS if not hasattr(db, name)]


def warn_if_client_is_stale() -> list[str]:
    """Say loudly at startup if the client doesn't match the schema.

    Without this the bot looks healthy and only fails later, when an admin
    tries to save something.
    """
    missing = missing_models()
    if missing:
        logger.error(
            "The generated Prisma client is out of date - missing: %s. "
            "Anything using those tables will fail. From the bot/ folder run: "
            "prisma db push --schema=database/schema.prisma "
            "&& prisma generate --schema=database/schema.prisma",
            ", ".join(missing),
        )
    return missing
