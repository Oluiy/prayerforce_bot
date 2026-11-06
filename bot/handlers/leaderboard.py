import logging

import keyboards
import messages
from keyboards import LEADERBOARD_CALLBACK
from services import quiz_service
from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)


async def view_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await quiz_service.get_leaderboard():
        await update.message.reply_text(messages.LEADERBOARD_EMPTY, parse_mode="HTML")
        return

    await update.message.reply_text(
        messages.LEADERBOARD_TEASER,
        reply_markup=keyboards.view_results_markup(messages.LEADERBOARD_DETAILS_BUTTON),
        parse_mode="HTML",
    )


async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.data.startswith(LEADERBOARD_CALLBACK):
        await query.answer()
        return

    parts = query.data.split("_", 2)
    quiz_id = parts[2] if len(parts) == 3 else None

    result = await quiz_service.get_leaderboard(quiz_id=quiz_id)
    if not result:
        await query.answer(text=messages.LEADERBOARD_UNAVAILABLE, show_alert=True)
        return

    title_suffix, entries = result
    try:
        await query.answer(text=messages.leaderboard_popup(entries), show_alert=True)
    except Exception as e:
        logger.warning("Error showing alert: %s", e)
        await query.answer()

    await query.edit_message_text(text=messages.leaderboard(title_suffix, entries))


leaderboard_handler = CommandHandler("leaderboard", view_leaderboard)
leaderboard_callback_handler = CallbackQueryHandler(leaderboard_callback, pattern="^view_leaderboard(_.*)?$")
