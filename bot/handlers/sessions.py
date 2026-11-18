"""/new_session: move the bot on to a new session (e.g. 2026/2027).

Members of the old session are asked whether they're continuing. Only those
who say yes, plus anyone who sends /start, get messages in the new session.
Nobody's records are deleted.
"""
import asyncio
import logging

import keyboards
import messages
from repositories import user_repository
from services import session_service
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils.auth import can_manage_admins

logger = logging.getLogger(__name__)

ASK_SESSION, CONFIRM = range(40, 42)

# Telegram allows about 30 messages a second; stay well under it.
INVITE_GAP_SECONDS = 0.05


async def start_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not can_manage_admins(update.effective_user):
        await update.message.reply_text(messages.NEW_SESSION_NOT_AUTHORIZED)
        return ConversationHandler.END

    current = session_service.current()
    suggested = session_service.next_after(current)
    await update.message.reply_text(
        messages.new_session_ask(current, await session_service.member_count(), suggested),
        reply_markup=keyboards.new_session_suggest_markup(suggested),
        parse_mode="HTML",
    )
    return ASK_SESSION


async def picked_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "newsess_cancel":
        return await cancel_new_session(update, context)
    return await _confirm(query.edit_message_text, context, query.data.replace("newsess_pick_", ""))


async def typed_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        session = session_service.parse(update.message.text)
    except session_service.SessionError as e:
        await update.message.reply_text(messages.new_session_rejected(str(e)), parse_mode="HTML")
        return ASK_SESSION
    return await _confirm(update.message.reply_text, context, session)


async def _confirm(send, context, session: str):
    current = session_service.current()
    if session == current:
        await send(
            messages.new_session_rejected(f"{session} is already the current session."),
            parse_mode="HTML",
        )
        return ASK_SESSION

    context.user_data["new_session"] = session
    await send(
        messages.new_session_confirm(current, session, await session_service.member_count()),
        reply_markup=keyboards.new_session_confirm_markup(),
        parse_mode="HTML",
    )
    return CONFIRM


async def confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "newsess_cancel":
        return await cancel_new_session(update, context)

    session = context.user_data.pop("new_session", None)
    if not session:
        await query.edit_message_text(messages.MENU_EXPIRED)
        return ConversationHandler.END

    _, invitees = await session_service.start_new(session, started_by=str(update.effective_user.id))
    sent, failed = await _invite(context.bot, invitees, session)
    await query.edit_message_text(messages.new_session_started(session, sent, failed), parse_mode="HTML")
    return ConversationHandler.END


async def _invite(bot, invitees, session: str):
    sent = failed = 0
    for user in invitees:
        try:
            await bot.send_message(
                chat_id=user.chatId,
                text=messages.session_invite(session, user.firstName or "friend"),
                reply_markup=keyboards.session_invite_markup(session),
                parse_mode="HTML",
            )
            sent += 1
        except Exception as e:
            logger.warning("Could not invite %s into %s: %s", user.chatId, session, e)
            failed += 1
        await asyncio.sleep(INVITE_GAP_SECONDS)
    return sent, failed


async def cancel_new_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_session", None)
    if update.callback_query:
        await update.callback_query.edit_message_text(messages.NEW_SESSION_CANCELLED)
    else:
        await update.message.reply_text(messages.NEW_SESSION_CANCELLED)
    return ConversationHandler.END


# --- A member answering the invitation -----------------------------------------
async def answered_invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    joining = query.data.startswith("sessjoin_")
    session = query.data.split("_", 1)[1]
    # An old button from a previous rollover mustn't sign someone up to the wrong year.
    if session != session_service.current():
        await query.edit_message_text(messages.SESSION_INVITE_OLD)
        return

    user = await user_repository.get_or_create(update.effective_user)
    if joining:
        await session_service.join(user)
        await query.edit_message_text(messages.session_joined(session), parse_mode="HTML")
    else:
        await session_service.leave(user)
        await query.edit_message_text(messages.session_left(session), parse_mode="HTML")


new_session_handler = ConversationHandler(
    entry_points=[CommandHandler("new_session", start_new_session)],
    states={
        ASK_SESSION: [
            CallbackQueryHandler(picked_session, pattern="^newsess_(pick_|cancel)"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, typed_session),
        ],
        CONFIRM: [CallbackQueryHandler(confirmed, pattern="^newsess_(confirm|cancel)")],
    },
    fallbacks=[CommandHandler("cancel", cancel_new_session)],
    conversation_timeout=5 * 60,
)
session_invite_handler = CallbackQueryHandler(answered_invite, pattern="^sess(join|leave)_")
