import logging

from telegram.ext import ContextTypes

from services.birthday_service import greet_todays_birthdays

logger = logging.getLogger(__name__)


async def send_birthday_messages(context: ContextTypes.DEFAULT_TYPE):
    logger.info("Running send_birthday_messages job...")
    sent = await greet_todays_birthdays(context.bot)
    logger.info("Sent %s birthday message(s).", sent)
