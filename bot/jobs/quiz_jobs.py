"""Scheduled quiz jobs. Each job calls the quiz service, then announces the result."""
import datetime
import logging

from telegram.ext import ContextTypes

import messages
from handlers.leaderboard import view_results_markup
from services import broadcast_service, quiz_service
from utils.dates import is_last_day_of_month, utc_now

logger = logging.getLogger(__name__)


async def open_weekly_quiz(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Running open_weekly_quiz job...")
    if await quiz_service.open_weekly_quiz():
        await broadcast_service.broadcast_text(context.bot, messages.WEEKLY_QUIZ_OPEN, parse_mode="Markdown")


async def open_daily_quiz(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Running open_daily_quiz job...")
    if await quiz_service.open_daily_quiz():
        await broadcast_service.broadcast_text(context.bot, messages.DAILY_QUIZ_OPEN, parse_mode="Markdown")


async def close_daily_quiz(context: ContextTypes.DEFAULT_TYPE):
    """Close today's quiz, add scores to the monthly totals and announce the winner."""
    logger.info("Running close_daily_quiz job...")
    quiz, scores = await quiz_service.close_active_quiz("daily", order_by="createdAt")
    if not quiz:
        logger.info("No active daily quiz found to close.")
        return

    await quiz_service.add_scores_to_monthly_totals(scores, utc_now())

    if scores:
        winner = scores[0]
        await broadcast_service.broadcast_text(
            context.bot,
            messages.daily_winner(winner.user.firstName, winner.score),
            parse_mode="Markdown",
        )


async def close_weekly_quiz(context: ContextTypes.DEFAULT_TYPE):
    """Close the weekly quiz and send everyone a button to view the results."""
    logger.info("Running close_weekly_quiz job...")
    quiz, _ = await quiz_service.close_active_quiz("weekly", order_by="weekStart")
    if not quiz:
        logger.info("No active quiz found to close.")
        return

    await broadcast_service.broadcast_text(
        context.bot,
        messages.WEEKLY_QUIZ_CLOSED,
        reply_markup=view_results_markup(messages.VIEW_RESULTS_BUTTON, quiz_id=quiz.id),
        parse_mode="Markdown",
    )


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
    """On the last day of the month, build a recap quiz from past weekly questions."""
    today = datetime.datetime.now()
    if not is_last_day_of_month(today):
        return

    logger.info("Generating Monthly Recap Quiz...")
    question_count = await quiz_service.create_monthly_recap(today)
    if not question_count:
        logger.info("No questions found for monthly recap.")
        return

    await broadcast_service.broadcast_text(
        context.bot, messages.monthly_recap_released(question_count), parse_mode="Markdown"
    )
