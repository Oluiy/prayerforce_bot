from telegram import *
from telegram.ext import *
from Prisma.prisma_connect import db
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AWAITING_MESSAGE = range(1)

COUNSELLOR_CHAT_IDS = [5352757845, 661560390]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi — use /counsel to send a private counsel request.")


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
    forward_text = (
        f"📩 *New counsel request*\n\n"
        f"*From:* {name if name else ''} (name: `{name}`)\n"
        f"{f'*Phone:* {phone}\\n' if phone else ''}\n"
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



conv = ConversationHandler(
    entry_points=[CommandHandler("counsel", counsel_command)],
    states={
        AWAITING_MESSAGE: [MessageHandler(filters.TEXT | filters.CONTACT, receive_message)]
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_user=True,
    per_chat=True
)