"""Birthday greetings."""
import datetime
import logging

import messages
from config.constants import TIMEZONE
from repositories import user_repository

logger = logging.getLogger(__name__)


async def send_birthday_message(bot, user, mates):
    text = messages.birthday(user.firstName or "friend", [m.firstName for m in mates if m.firstName])
    await bot.send_message(chat_id=user.chatId, text=text)


async def greet_todays_birthdays(bot):
    """Send a greeting to everyone whose birthday is today. Returns how many were sent."""
    today = datetime.datetime.now(TIMEZONE).date()
    birthday_users = await user_repository.list_by_birthday(today)
    sent = 0
    for user in birthday_users:
        mates = [u for u in birthday_users if u.chatId != user.chatId]
        try:
            await send_birthday_message(bot, user, mates)
            sent += 1
        except Exception as e:
            logger.warning("Failed to send birthday message to %s: %s", user.chatId, e)
    return sent
