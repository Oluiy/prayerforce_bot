import logging

import messages
from repositories import user_repository
from services import session_service
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await user_repository.get_or_create(update.effective_user)
    # Saying hello is how someone joins this session's mailing list.
    try:
        await session_service.join(user)
    except Exception:
        logger.exception("Could not add %s to the current session", user.chatId)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages.welcome(update.effective_user.first_name),
        parse_mode="HTML",
    )
    return user


start_handler = CommandHandler("start", start)
# Any text message containing "start" also triggers the welcome message.
start_text_handler = MessageHandler(filters.TEXT & filters.Regex(r"start"), start)
