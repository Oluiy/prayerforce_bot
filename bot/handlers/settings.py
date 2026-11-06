"""/settings — admins change times, prices and quiz rules from inside Telegram.

Changes take effect immediately: text is read fresh on each message, and the
recurring jobs are rescheduled on save.
"""
import logging

import keyboards
import messages
from services import settings_service
from telegram import Update
from utils.auth import is_admin
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

logger = logging.getLogger(__name__)

WAITING_VALUE = 20

# Set by main.py so a saved time can reschedule its job without a restart.
_on_change = None


def set_change_callback(callback):
    global _on_change
    _on_change = callback


async def show_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text(messages.SETTINGS_NOT_AUTHORIZED)
        return ConversationHandler.END

    await update.message.reply_text(
        messages.SETTINGS_HEADER,
        reply_markup=keyboards.settings_markup(settings_service.current_values()),
        parse_mode="Markdown",
    )
    return WAITING_VALUE


async def chose_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user):
        return ConversationHandler.END
    if query.data == "setting_done":
        await query.edit_message_text(messages.SETTINGS_CANCELLED)
        return ConversationHandler.END

    key = query.data.replace("setting_", "")
    if key not in settings_service.BY_KEY:
        return ConversationHandler.END

    context.user_data["editing_setting"] = key
    definition = settings_service.definition(key)
    await query.edit_message_text(
        messages.settings_ask_value(definition, settings_service.get(key)), parse_mode="Markdown"
    )
    return WAITING_VALUE


async def receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get("editing_setting")
    if not key:
        return ConversationHandler.END

    definition = settings_service.definition(key)
    try:
        value = definition.parse(update.message.text)
    except ValueError as e:
        await update.message.reply_text(messages.settings_rejected(str(e)), parse_mode="Markdown")
        return WAITING_VALUE

    try:
        await settings_service.set(key, value, updated_by=str(update.effective_user.id))
    except Exception:
        logger.exception("Could not save setting %s", key)
        await update.message.reply_text(messages.SETTINGS_SAVE_FAILED)
        return ConversationHandler.END

    await update.message.reply_text(messages.settings_saved(definition, value), parse_mode="Markdown")

    # A changed job time needs the job put back on the queue at the new time.
    if definition.kind == settings_service.TIME and _on_change:
        try:
            _on_change(context.application)
        except Exception:
            logger.exception("Could not reschedule jobs after changing %s", key)

    context.user_data.pop("editing_setting", None)
    return ConversationHandler.END


async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("editing_setting", None)
    await update.message.reply_text(messages.SETTINGS_CANCELLED)
    return ConversationHandler.END


settings_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", show_settings)],
    states={
        WAITING_VALUE: [
            CallbackQueryHandler(chose_setting, pattern="^setting_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_value),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_settings)],
)
