from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv
import os
from database.prisma_connect import db
from telegram.constants import ParseMode

load_dotenv()
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_ID_LEGACY = os.getenv("ADMIN_ID", "")
ADMIN_IDS = set()
for id_part in f"{ADMIN_IDS_STR},{ADMIN_ID_LEGACY}".split(","):
    clean_id = id_part.strip()
    if clean_id.isdigit():
        ADMIN_IDS.add(int(clean_id))

WAITING_BROADCAST_MESSAGE = 1

async def start_manual_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Restrict to admins
    if not user or user.id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to broadcast messages.")
        return ConversationHandler.END

    await update.message.reply_text(
        "Please send the message you want to broadcast to all users.\n\n"
        "Send /cancel to abort."
    )
    return WAITING_BROADCAST_MESSAGE

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        await update.message.reply_text("Please send a valid message.")
        return WAITING_BROADCAST_MESSAGE
        
    status_msg = await update.message.reply_text("Broadcasting... Please wait.")
    
    users = await db.user.find_many()
    success_count = 0
    fail_count = 0
    
    for user in users:
        try:
            await context.bot.copy_message(
                chat_id=user.chatId,
                from_chat_id=update.message.chat_id,
                message_id=update.message.message_id
            )
            success_count += 1
        except Exception as e:
            print(f"Error sending broadcast to {user.firstName}: {e}")
            fail_count += 1
            
    await status_msg.edit_text(
        f"✅ Broadcast Complete!\n\n"
        f"Successfully sent to: {success_count} users.\n"
        f"Failed to send to: {fail_count} users."
    )
    return ConversationHandler.END

async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Broadcast cancelled.")
    return ConversationHandler.END

manual_broadcast_handler = ConversationHandler(
    entry_points=[CommandHandler("broadcastmessage", start_manual_broadcast)],
    states={
        WAITING_BROADCAST_MESSAGE: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_broadcast_message)],
    },
    fallbacks=[CommandHandler("cancel", cancel_broadcast)]
)
