
"""Scheduled reminders for weekly prayer meetings."""

import logging

import messages
from services import broadcast_service, settings_service
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# Which /settings value holds each day's pre-service prayer time.
PRE_SERVICE_SETTING = {
    "Tuesday": "tuesday_service_time",
    "Thursday": "thursday_service_time",
    "Sunday": "pre_service_time",
}


async def send_meeting_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Send the reminder for the next day's prayer meeting."""

    service_day = context.job.data

    pre_service_time = settings_service.get(PRE_SERVICE_SETTING[service_day])

    post_service_time = None

    if service_day == "Sunday":
        post_service_time = settings_service.get("post_service_time")

    reminder = messages.meeting_reminder(
        service_day,
        pre_service_time,
        post_service_time,
    )

    sent, failed = await broadcast_service.broadcast_text(
        context.bot,
        reminder,
        parse_mode="HTML",
    )

    logger.info(
        "%s meeting reminder sent. Successful: %s, Failed: %s",
        service_day,
        sent,
        failed,
    )
