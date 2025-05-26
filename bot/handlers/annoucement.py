from telegram import Update
from telegram.ext import ContextTypes, CommandHandler


async def announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = (
        "Get Edified🥰🙏 !!!\n\n\n"
        "We’ll be going before the Lord by 5:30pm today with hearts ready to seek Him. "
        "Tell a Prayer Force member to tell a Prayer Force member to tell another Prayer Force member "
        "that today's meeting is not one you want to miss."
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=message_text)


annoucement_handler = CommandHandler("announcement", announcement)
