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
