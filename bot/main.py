"""Entry point: python main.py (run from the bot/ folder)."""
import asyncio
import logging

from telegram.ext import ApplicationBuilder

from config import settings
from database.prisma_connect import db
from handlers import register_handlers
from handlers.menu import set_bot_commands
from jobs import schedule_jobs

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
        await db.connect()
        logger.info("Database connected successfully!")
    except Exception as e:
        logger.error("Failed to connect to database: %s", e)
        return

    application = (
        ApplicationBuilder().token(settings.telegram_bot_token).post_init(set_bot_commands).build()
    )
    register_handlers(application)
    schedule_jobs(application.job_queue)

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
