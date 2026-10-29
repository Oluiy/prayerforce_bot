from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, MessageHandler, filters

import messages
from repositories import user_repository


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await user_repository.get_or_create(update.effective_user)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=messages.welcome(update.effective_user.first_name),
        parse_mode="Markdown",
    )
    return user


start_handler = CommandHandler("start", start)
# Any text message containing "start" also triggers the welcome message.
start_text_handler = MessageHandler(filters.TEXT & filters.Regex(r"start"), start)
