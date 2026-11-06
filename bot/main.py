"""Entry point: python main.py (run from the bot/ folder)."""
import asyncio
import logging

from config import settings
from database.prisma_connect import connect_with_retry, db, warn_if_client_is_stale
from handlers import register_handlers
from handlers.menu import set_bot_commands
from handlers.settings import set_change_callback
from jobs import reschedule_jobs, schedule_jobs
from services import admin_service, settings_service
from telegram.ext import ApplicationBuilder

logger = logging.getLogger(__name__)


def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, force=True
    )
    # Avoid logging raw Telegram request URLs that include the bot token.
    for noisy in ("httpx", "httpcore", "telegram.request"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def main():
    setup_logging()
    logger.info("Starting bot...")

    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        return

    try:
        await connect_with_retry()
        logger.info("Database connected successfully!")
        warn_if_client_is_stale()
    except Exception as e:
        logger.error("Failed to connect to database: %s", e)
        return

    # Admin-changed settings decide the job times, so load them first.
    await settings_service.load()
    # Live temporary-admin grants, so access survives a restart.
    await admin_service.load()

    application = (
        ApplicationBuilder().token(settings.telegram_bot_token).post_init(set_bot_commands).build()
    )
    register_handlers(application)
    schedule_jobs(application.job_queue)
    # Lets /settings move a job's time without a restart.
    set_change_callback(reschedule_jobs)

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    logger.info("Bot is up and running! 🚀")

    try:
        await asyncio.Event().wait()
    finally:
        await db.disconnect()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
