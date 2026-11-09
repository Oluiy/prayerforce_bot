"""Registering the recurring jobs.

Quiz opening and closing is *not* here: each quiz carries its own times and
the sweep acts on them. Only jobs with no quiz behind them are scheduled by
the clock, and their times come from /settings.
"""
import logging
from datetime import datetime, time

from config import settings
from config.constants import (
    ADMIN_EXPIRY_SWEEP_SECONDS,
    SCHEDULE_SWEEP_SECONDS,
    TIMEZONE,
)

from services import settings_service
from telegram.ext import Application, JobQueue

from jobs.admin_jobs import expire_admin_grants
from jobs.birthday_jobs import send_birthday_messages
from jobs.keepalive import PING_FIRST_SECONDS, PING_INTERVAL_SECONDS, self_ping
from jobs.meeting_jobs import send_meeting_reminder
from jobs.quiz_jobs import (
    generate_monthly_recap,
    send_monthly_cumulative_leaderboard,
    sweep_quiz_schedule,
)

logger = logging.getLogger(__name__)

SWEEP_JOB = "quiz_schedule_sweep"
ADMIN_EXPIRY_JOB = "admin_expiry_sweep"
KEEPALIVE_JOB = "keepalive_ping"

# job name -> (callback, settings key holding its time)
DAILY_JOBS = {
    "monthly_leaderboard": (send_monthly_cumulative_leaderboard, "monthly_leaderboard_time"),
    "monthly_recap": (generate_monthly_recap, "monthly_recap_time"),
    "birthday_messages": (send_birthday_messages, "birthday_message_time"),
}


def _local(value: time) -> time:
    local_date = datetime.now(TIMEZONE).date()
    local_datetime = TIMEZONE.localize(datetime.combine(local_date, value))
    return local_datetime.timetz()


def schedule_jobs(job_queue: JobQueue):
    """Register the sweep and the daily jobs. Called once at startup."""
    job_queue.run_repeating(
        sweep_quiz_schedule, interval=SCHEDULE_SWEEP_SECONDS, first=5, name=SWEEP_JOB
    )
    job_queue.run_repeating(
        expire_admin_grants, interval=ADMIN_EXPIRY_SWEEP_SECONDS, first=10, name=ADMIN_EXPIRY_JOB
    )

    # Only deployed instances have a public URL to ping.
    if settings.public_url:
        job_queue.run_repeating(
            self_ping,
            interval=PING_INTERVAL_SECONDS,
            first=PING_FIRST_SECONDS,
            name=KEEPALIVE_JOB,
        )
        logger.info("Self-ping every %s seconds", PING_INTERVAL_SECONDS)

    _schedule_daily_jobs(job_queue)
    _schedule_meeting_reminders(job_queue)


def _schedule_daily_jobs(job_queue: JobQueue):
    for name, (callback, settings_key) in DAILY_JOBS.items():
        at = _local(settings_service.get(settings_key))
        job_queue.run_daily(callback, time=at, name=name)
        logger.info("Scheduled %s at %s", name, at.strftime("%H:%M %Z"))


def _schedule_meeting_reminders(job_queue: JobQueue):
    """Schedule reminders on the night before each service."""

    reminders = [
        (
            "tuesday_meeting_reminder",
            "tuesday_meeting_reminder_time",
            1,  # Monday
            "Tuesday",
        ),
        (
            "thursday_meeting_reminder",
            "thursday_meeting_reminder_time",
            3,  # Wednesday
            "Thursday",
        ),
        (
            "sunday_meeting_reminder",
            "sunday_meeting_reminder_time",
            6,  # Saturday
            "Sunday",
        ),
    ]

    for name, settings_key, reminder_day, service_day in reminders:
        at = _local(settings_service.get(settings_key))

        job_queue.run_daily(
            send_meeting_reminder,
            time=at,
            days=(reminder_day,),
            data=service_day,
            name=name,
        )

        logger.info(
            "Scheduled %s for %s at %s",
            name,
            service_day,
            at.strftime("%H:%M %Z"),
        )


def reschedule_jobs(app: Application):
    """Reschedule daily jobs and meeting reminders after settings change."""

    job_names = [
        *DAILY_JOBS.keys(),
        "tuesday_meeting_reminder",
        "thursday_meeting_reminder",
        "sunday_meeting_reminder",
    ]

    for name in job_names:
        for job in app.job_queue.get_jobs_by_name(name):
            job.schedule_removal()

    _schedule_daily_jobs(app.job_queue)
    _schedule_meeting_reminders(app.job_queue)
