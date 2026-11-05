"""Registering the recurring jobs.

Quiz opening and closing is *not* here: each quiz carries its own times and
the sweep acts on them. Only jobs with no quiz behind them run by the clock.
"""
import logging
from datetime import time

from telegram.ext import JobQueue

from config import constants as c
from jobs.birthday_jobs import send_birthday_messages
from jobs.quiz_jobs import (
    generate_monthly_recap,
    send_monthly_cumulative_leaderboard,
    sweep_quiz_schedule,
)

logger = logging.getLogger(__name__)

SWEEP_JOB = "quiz_schedule_sweep"


def _local(value: time) -> time:
    return time(hour=value.hour, minute=value.minute, tzinfo=c.TIMEZONE)


def schedule_jobs(job_queue: JobQueue):
    """Register the sweep and the daily jobs. Called once at startup."""
    job_queue.run_repeating(
        sweep_quiz_schedule, interval=c.SCHEDULE_SWEEP_SECONDS, first=5, name=SWEEP_JOB
    )

    # These run every day; the jobs themselves only act on the last day of the month.
    job_queue.run_daily(send_monthly_cumulative_leaderboard, time=_local(c.MONTHLY_LEADERBOARD_TIME))
    job_queue.run_daily(generate_monthly_recap, time=_local(c.MONTHLY_RECAP_TIME))

    job_queue.run_daily(send_birthday_messages, time=_local(c.BIRTHDAY_MESSAGE_TIME))
