from telegram import *
from telegram.ext import *
from database.prisma_connect import db
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWAITING_MESSAGE = range(1)

import os

# Load from .env, expecting a comma-separated list of IDs
counsellor_ids_str = os.getenv("COUNSELLOR_CHAT_IDS", "")
try:
    COUNSELLOR_CHAT_IDS = [int(id.strip()) for id in counsellor_ids_str.split(",") if id.strip()]
except ValueError:
    print("Warning: invalid COUNSELLOR_CHAT_IDS in .env, defaulting to empty list.")
    COUNSELLOR_CHAT_IDS = []

if not COUNSELLOR_CHAT_IDS:
    COUNSELLOR_CHAT_IDS = [5352757845]
    print(f"Using default COUNSELLOR_CHAT_IDS: {COUNSELLOR_CHAT_IDS}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi — use /counsel to send a private counsel request.")

# description: Hava a prayer request, let us pray with you 
async def let_us_pray_with_you(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Let us pray with you", callback_data="prayer_request", url="https://bit.ly/LetUsPrayWithYou")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Do you have a prayer request? Click the button below to share it with our prayer team, and we'll pray with you! 🙏", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Do you have a prayer request? Click the button below to share it with our prayer team, and we'll pray with you! 🙏", reply_markup=reply_markup)

async def prayer_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(f"Please send your prayer request to {https://bit.ly/LetUsPrayWithYou}")


async def counsel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [KeyboardButton("Share contact", request_contact=True)],
    ]
    await update.message.reply_text(
        "Please send your message for counselling. "
        "If you want the counsellors to have your phone number, press *Share contact* first.",
        reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True),
        parse_mode="Markdown",
    )
    return AWAITING_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    tg_id = user.id
    name = user.first_name
    username = user.username
    phone = None

    if update.message.contact:
        phone = update.message.contact.phone_number
        await update.message.reply_text("Thanks for sharing contact. Now send your message.")
        return AWAITING_MESSAGE

    text = update.message.text
    if not text:
        await update.message.reply_text("I didn't get any text. Please send your counselling message.")
        return AWAITING_MESSAGE

    # acknowledgement
    await update.message.reply_text("you will get a response latest in the next 24 hours")

    # Save in DB with Prisma
    # try:
    #     created = await db.counselrequest.create(
    #         data={
    #             "telegramId": tg_id,
    #             "username": username,
    #             "phoneNumber": phone,
    #             "message": text,
    #             "responseDueAt": datetime.,
    #         }
    #     )
    #     logger.info("Saved counsel request id=%s", created.id)
    # except Exception as e:
    #     logger.exception("Error saving counsel request: %s", e)

    # Notify counsellors
    # Prepare phone info safely
    phone_line = f"*Phone:* {phone}\n" if phone else ""
    forward_text = (
        f"📩 *New counsel request*\n\n"
        f"*From:* {name if name else ''} (name: `{name}`)\n"
        f"{phone_line}"
        f"*Message:*\n{text}"
    )

    for chat_id in COUNSELLOR_CHAT_IDS:
        try:
            await context.bot.send_message(chat_id=chat_id, text=forward_text, parse_mode="Markdown")
        except Exception as e:
            logger.exception("Failed to notify counsellor %s: %s", chat_id, e)

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END




pr_request = CommandHandler("prayer_request", let_us_pray_with_you)
# conv = ConversationHandler(
#     entry_points=[],
#     states={
#         AWAITING_MESSAGE: [MessageHandler(filters.TEXT | filters.CONTACT, receive_message)]
#     },
#     fallbacks=[CommandHandler("cancel", cancel)],
#     per_user=True,
#     per_chat=True
# )