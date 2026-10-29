from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CommandHandler, ContextTypes

import messages
from config.constants import PRAYER_REQUEST_URL, TESTIMONY_FORM_URL


async def _reply_with_link(update: Update, text: str, button_text: str, callback_data: str, url: str):
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(button_text, callback_data=callback_data, url=url)]]
    )
    message = update.message or (update.callback_query and update.callback_query.message)
    if message:
        await message.reply_text(text, reply_markup=reply_markup)


async def let_us_pray_with_you(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply_with_link(
        update, messages.PRAYER_REQUEST_PROMPT, messages.PRAYER_REQUEST_BUTTON,
        "prayer_request", PRAYER_REQUEST_URL,
    )


async def share_testimony(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _reply_with_link(
        update, messages.TESTIMONY_PROMPT, messages.TESTIMONY_BUTTON,
        "share_testimony", TESTIMONY_FORM_URL,
    )


prayer_request_handler = CommandHandler("prayer_request", let_us_pray_with_you)
testimony_handler = CommandHandler("share_testimony", share_testimony)
