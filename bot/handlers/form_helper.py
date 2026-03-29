from telegram import *
from telegram.ext import *
from database.prisma_connect import db
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# description: Hava a prayer request, let us pray with you 
async def let_us_pray_with_you(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Let us pray with you", callback_data="prayer_request", url="https://bit.ly/LetUsPrayWithYou")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("Do you have a prayer request? Click the button below to share it with our prayer team, and we'll pray with you! 🙏", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text("Do you have a prayer request? Click the button below to share it with our prayer team, and we'll pray with you! 🙏", reply_markup=reply_markup)

async def share_testimony(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Share your testimony", callback_data="share_testimony", url="https://forms.gle/btif8k48fPW9Lh6g7")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(f"Hello beloved, \nWe’d love to celebrate what God is doing in your life 🤍", reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.message.reply_text(f"Hello beloved, \nWe’d love to celebrate what God is doing in your life 🤍", reply_markup=reply_markup)


pr_request = CommandHandler("prayer_request", let_us_pray_with_you)
testimony_request = CommandHandler("share_testimony", share_testimony)
