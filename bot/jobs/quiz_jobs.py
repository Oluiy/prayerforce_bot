"""Scheduled quiz jobs.

Opening and closing is driven by each quiz's own `opensAt`/`closesAt`, so the
sweep below replaces the old fixed daily open/close jobs. It is safe to miss
runs: it works from the stored times, so a restart just means the next sweep
catches up.
"""
import datetime
import logging

import messages
import notifications
from services import broadcast_service, quiz_service
from telegram.ext import ContextTypes
from utils.dates import is_last_day_of_month, utc_now

logger = logging.getLogger(__name__)


async def sweep_quiz_schedule(context: ContextTypes.DEFAULT_TYPE):
    """Open and close quizzes whose times have arrived."""
    try:
        result = await quiz_service.run_schedule_sweep()
    except Exception:
        logger.exception("Quiz schedule sweep failed")
        return

    for quiz in result.opened:
        await notifications.announce_quiz_open(context.bot, quiz)

    for quiz, scores in result.closed:
        await notifications.announce_quiz_closed(context.bot, quiz, scores)


async def send_monthly_cumulative_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    """On the last day of the month, send the month's top daily-quiz scorers."""
    today = utc_now()
    if not is_last_day_of_month(today):
        return

    month_year = today.strftime("%Y-%m")
    logger.info("Sending monthly cumulative leaderboard...")
    entries = await quiz_service.get_monthly_leaderboard(month_year)
    if not entries:
        logger.info("No cumulative scores found for %s", month_year)
        return

    await broadcast_service.broadcast_text(
        context.bot,
        messages.monthly_leaderboard(today.strftime("%B %Y"), entries),
        parse_mode="Markdown",
    )
    logger.info("Monthly cumulative leaderboard sent for %s", month_year)


async def generate_monthly_recap(context: ContextTypes.DEFAULT_TYPE):
    """On the last day of the month, build a recap quiz from past weekly questions.

    It opens straight away and runs for a week, since no admin is here to
    choose a window.
    """
    today = datetime.datetime.now()
    if not is_last_day_of_month(today):
        return

    logger.info("Generating Monthly Recap Quiz...")
    opens_at = utc_now()
    result = await quiz_service.create_monthly_recap(
        today, opens_at=opens_at, closes_at=opens_at + datetime.timedelta(days=7)
    )
    if not result:
        logger.info("No questions found for monthly recap.")
        return

    quiz, question_count = result
    await broadcast_service.broadcast_text(
        context.bot, messages.monthly_recap_released(question_count), parse_mode="Markdown"
    )
