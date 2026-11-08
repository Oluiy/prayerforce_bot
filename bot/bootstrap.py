"""Shared startup and shutdown for both entry points.

`main.py` runs the bot with long polling (local development). `web.py` runs the
same bot behind uvicorn with a Telegram webhook (deployment). Building the
Application in one place keeps handlers, jobs, timers and in-memory state
identical between the two.
"""
import logging

from config import settings
from database.prisma_connect import connect_with_retry, db, warn_if_client_is_stale
from handlers import register_handlers
from handlers.menu import set_bot_commands
from handlers.settings import set_change_callback
from jobs import reschedule_jobs, schedule_jobs
from services import admin_service, settings_service
from telegram.ext import Application, ApplicationBuilder

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, force=True
    )
    # Avoid logging raw Telegram request URLs that include the bot token.
    for noisy in ("httpx", "httpcore", "telegram.request"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def build_application(polling: bool) -> Application:
    """Connect to the database and build the Application, ready to start.

    Raises instead of returning a half-working bot: behind a webhook a silent
    failure would still answer /health while doing nothing useful.
    """
    setup_logging()
    logger.info("Starting bot...")

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set.")

    await connect_with_retry()
    logger.info("Database connected successfully!")
    warn_if_client_is_stale()

    # Admin-changed settings decide the job times, so load them first.
    await settings_service.load()
    # Live temporary-admin grants, so access survives a restart.
    await admin_service.load()

    builder = ApplicationBuilder().token(settings.telegram_bot_token)
    if not polling:
        # No updater: uvicorn receives the updates and queues them itself.
        builder = builder.updater(None)
    application = builder.build()

    register_handlers(application)
    schedule_jobs(application.job_queue)
    # Lets /settings move a job's time without a restart.
    set_change_callback(reschedule_jobs)

    await application.initialize()
    # Not done via post_init: python-telegram-bot only runs that from
    # run_polling()/run_webhook(), and we drive the lifecycle ourselves.
    try:
        await set_bot_commands(application)
    except Exception:
        logger.exception("Could not set the command menus")

    return application


async def shutdown_application(application: Application):
    """Stop the app and close the database, whatever state it is in."""
    try:
        await application.stop()
    except Exception:
        logger.exception("Error while stopping the application")
    try:
        await application.shutdown()
    except Exception:
        logger.exception("Error while shutting down the application")

    await db.disconnect()
    logger.info("Bot stopped.")
