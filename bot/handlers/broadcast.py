from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

import messages
from services import broadcast_service
from utils.auth import is_admin

WAITING_BROADCAST_MESSAGE = 1


async def start_manual_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text(messages.BROADCAST_NOT_AUTHORIZED)
        return ConversationHandler.END

    await update.message.reply_text(messages.BROADCAST_ASK_MESSAGE)
    return WAITING_BROADCAST_MESSAGE


async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return WAITING_BROADCAST_MESSAGE

    status_msg = await update.message.reply_text(messages.BROADCAST_IN_PROGRESS)
    sent, failed = await broadcast_service.broadcast_copy(
        context.bot, from_chat_id=update.message.chat_id, message_id=update.message.message_id
    )
    await status_msg.edit_text(messages.broadcast_complete(sent, failed))
    return ConversationHandler.END


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.BROADCAST_CANCELLED)
    return ConversationHandler.END


manual_broadcast_handler = ConversationHandler(
    entry_points=[CommandHandler("broadcastmessage", start_manual_broadcast)],
    states={
        WAITING_BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_broadcast_message)],
    },
    fallbacks=[CommandHandler("cancel", cancel_broadcast)],
)
