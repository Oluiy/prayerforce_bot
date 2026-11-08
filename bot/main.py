"""Entry point for local development: python main.py (run from the bot/ folder).

Uses long polling, so no public URL or tunnel is needed. Deployed instances
run web.py behind uvicorn instead; both build the bot from bootstrap.py.
"""
import asyncio
import logging

from bootstrap import build_application, shutdown_application
from telegram.ext import Application

logger = logging.getLogger(__name__)


async def main():
    application: Application = await build_application(polling=True)

    await application.start()
    await application.updater.start_polling()
    logger.info("Bot is up and running! 🚀")

    try:
        await asyncio.Event().wait()
    finally:
        await shutdown_application(application)


if __name__ == "__main__":
    asyncio.run(main())
