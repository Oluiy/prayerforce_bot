import messages
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.HISTORY)


async def sunday_meetings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.meetings())


async def purchase_shirt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.merch())


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=messages.OPERATION_CANCELLED)
    return ConversationHandler.END


history_handler = CommandHandler("history", history_command)
sunday_meetings_handler = CommandHandler("meetings", sunday_meetings_command)
purchase_shirt_handler = CommandHandler("merch", purchase_shirt_command)
