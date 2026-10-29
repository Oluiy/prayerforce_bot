from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

import messages


async def announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=messages.ANNOUNCEMENT)


announcement_handler = CommandHandler("announcement", announcement)
