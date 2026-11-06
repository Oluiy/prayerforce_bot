"""Registering the recurring jobs.

Quiz opening and closing is *not* here: each quiz carries its own times and
the sweep acts on them. Only jobs with no quiz behind them are scheduled by
the clock, and their times come from /settings.
"""
import logging
from datetime import time

from config.constants import (
    ADMIN_EXPIRY_SWEEP_SECONDS,
    SCHEDULE_SWEEP_SECONDS,
    TIMEZONE,
)
from services import settings_service
from telegram.ext import Application, JobQueue

from jobs.admin_jobs import expire_admin_grants
from jobs.birthday_jobs import send_birthday_messages
from jobs.quiz_jobs import (
    generate_monthly_recap,
    send_monthly_cumulative_leaderboard,
    sweep_quiz_schedule,
)

logger = logging.getLogger(__name__)

SWEEP_JOB = "quiz_schedule_sweep"
ADMIN_EXPIRY_JOB = "admin_expiry_sweep"

# job name -> (callback, settings key holding its time)
DAILY_JOBS = {
    "monthly_leaderboard": (send_monthly_cumulative_leaderboard, "monthly_leaderboard_time"),
    "monthly_recap": (generate_monthly_recap, "monthly_recap_time"),
    "birthday_messages": (send_birthday_messages, "birthday_message_time"),
}


def _local(value: time) -> time:
    return time(hour=value.hour, minute=value.minute, tzinfo=TIMEZONE)


def schedule_jobs(job_queue: JobQueue):
    """Register the sweep and the daily jobs. Called once at startup."""
    job_queue.run_repeating(
        sweep_quiz_schedule, interval=SCHEDULE_SWEEP_SECONDS, first=5, name=SWEEP_JOB
    )
    job_queue.run_repeating(
        expire_admin_grants, interval=ADMIN_EXPIRY_SWEEP_SECONDS, first=10, name=ADMIN_EXPIRY_JOB
    )
    _schedule_daily_jobs(job_queue)


def _schedule_daily_jobs(job_queue: JobQueue):
    for name, (callback, settings_key) in DAILY_JOBS.items():
        at = _local(settings_service.get(settings_key))
        job_queue.run_daily(callback, time=at, name=name)
        logger.info("Scheduled %s at %s", name, at.strftime("%H:%M %Z"))


def reschedule_jobs(app: Application):
    """Put the daily jobs back on the queue at their current times.

    Called after an admin changes a time in /settings, so the new time applies
    without restarting the bot.
    """
    for name in DAILY_JOBS:
        for job in app.job_queue.get_jobs_by_name(name):
            job.schedule_removal()
    _schedule_daily_jobs(app.job_queue)
