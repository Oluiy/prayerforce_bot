"""Love letters: this week's set, who has had one, and sending them out.

Letters are written per week. A send draws one random letter per member from
the current week's set, so two members can receive different letters. Direct
sends (an admin choosing a letter for one person) are extra and do not use up
that member's weekly letter.

This module knows nothing about Telegram beyond being handed a `bot` to send
with, so handlers and (later) scheduled jobs can share it.
"""
import asyncio
import logging
import random
import uuid

from config.constants import TIMEZONE
from repositories import love_letter_repository, user_repository
from utils.dates import local_now

logger = logging.getLogger(__name__)

MAX_LETTER_CHARS = 4000
# Telegram allows roughly 30 messages a second; keep well under it.
SEND_DELAY_SECONDS = 0.05
FALLBACK_NAME = "prayer force member"

WEEKLY = "weekly"
DIRECT = "direct"


class LoveLetterError(Exception):
    """A problem worth showing the admin, already safe to display."""


def week_key(moment=None) -> str:
    """The current week in TIMEZONE, e.g. "2026-W45" (ISO weeks, Monday start)."""
    moment = moment or local_now()
    iso = moment.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def render(body: str, first_name: str | None) -> str:
    """Fill {name} in a letter, falling back to a neutral greeting."""
    name = (first_name or "").strip() or FALLBACK_NAME
    return body.replace("{name}", name)


# --- Writing letters ---------------------------------------------------------
async def add_letter(body: str, key: str | None = None):
    """Save one letter for a week. Returns (letter, how many that week now has)."""
    text = (body or "").strip()
    if not text:
        raise LoveLetterError("that letter was empty.")
    if len(text) > MAX_LETTER_CHARS:
        raise LoveLetterError(
            f"that letter is too long ({len(text)} characters). "
            f"Please keep it under {MAX_LETTER_CHARS}."
        )

    key = key or week_key()
    letter = await love_letter_repository.create(text, key)
    count = await love_letter_repository.count_for_week(key)
    logger.info("Added love letter %s for %s", letter.id, key)
    return letter, count


async def letters_for_week(key: str | None = None):
    return await love_letter_repository.list_for_week(key or week_key())


async def remove_letter(letter_id):
    """Stop using a letter. Past deliveries keep pointing at it."""
    await love_letter_repository.deactivate(letter_id)
    logger.info("Removed love letter %s", letter_id)


async def overview(key: str | None = None):
    """Everything the admin hub shows: (week, letters, member_count, served)."""
    key = key or week_key()
    letters = await love_letter_repository.list_for_week(key)
    members = await user_repository.list_all()
    served = await love_letter_repository.count_deliveries(key, WEEKLY)
    return key, letters, members, served


# --- Sending -----------------------------------------------------------------
class SendReport:
    """What one send run did."""

    def __init__(self, pool_size: int, total: int):
        self.pool_size = pool_size
        self.total = total
        self.sent = 0
        self.failed = 0
        self.skipped = 0


async def send_weekly(bot, members=None, letters=None, now=None) -> SendReport:
    """Send one random letter from this week's set to every member who hasn't had one.

    Safe to run twice: members already served this week are skipped, so a
    restart or a double-click can't send the same person two letters.
    """
    key = week_key(now)
    letters = letters if letters is not None else await letters_for_week(key)
    if not letters:
        raise LoveLetterError("there are no letters for this week yet - add one first.")

    members = members if members is not None else await user_repository.list_all()
    already_served = await love_letter_repository.delivered_user_ids(key, WEEKLY)
    batch_id = str(uuid.uuid4())
    report = SendReport(pool_size=len(letters), total=len(members))

    for user in members:
        if user.id in already_served:
            report.skipped += 1
            continue

        letter = random.choice(letters)
        try:
            await bot.send_message(chat_id=user.chatId, text=render(letter.body, user.firstName))
        except Exception as e:
            logger.warning(
                "Could not send a love letter to %s (%s): %s", user.firstName, user.chatId, e
            )
            report.failed += 1
            continue

        try:
            await love_letter_repository.create_delivery(user.id, letter.id, WEEKLY, key, batch_id)
        except Exception:
            # The message went out; only the record failed. Don't report it as
            # unsent, or the admin may send it again.
            logger.exception("Sent a love letter but could not record it for %s", user.id)

        report.sent += 1
        await asyncio.sleep(SEND_DELAY_SECONDS)

    logger.info(
        "Love letter run %s: sent %s, failed %s, skipped %s (pool %s)",
        batch_id, report.sent, report.failed, report.skipped, report.pool_size,
    )
    return report


async def send_direct(bot, user, letter) -> None:
    """Send one chosen letter to one member, on top of their weekly one."""
    batch_id = str(uuid.uuid4())
    await bot.send_message(chat_id=user.chatId, text=render(letter.body, user.firstName))
    await love_letter_repository.create_delivery(
        user.id, letter.id, DIRECT, None, batch_id
    )
    logger.info("Sent a direct love letter (%s) to %s", letter.id, user.id)


async def pick_random_letter(letters):
    if not letters:
        raise LoveLetterError("there are no letters for this week yet - add one first.")
    return random.choice(letters)
