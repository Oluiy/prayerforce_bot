"""Giving a member admin access for a limited time, and taking it back.

Only permanent admins (ADMIN_IDS in .env) can use these, so a temporary
admin can't extend their own time or promote anyone else.
"""
import logging

import keyboards
import messages
from repositories import user_repository
from services import admin_service
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
from utils.dates import TimeParseError, format_duration_left, parse_duration

from handlers.menu import apply_admin_menu, apply_member_menu

logger = logging.getLogger(__name__)

ASK_MEMBER, PICK_MEMBER, ASK_DURATION = range(30, 33)

DURATION_PRESETS = [("30 minutes", 30), ("2 hours", 120), ("6 hours", 360), ("24 hours", 1440)]


# --- /make_admin -------------------------------------------------------------
async def start_make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not can_manage_admins(update.effective_user):
        await update.message.reply_text(messages.ADMIN_MANAGE_NOT_AUTHORIZED)
        return ConversationHandler.END

    await update.message.reply_text(messages.MAKE_ADMIN_ASK_MEMBER, parse_mode="HTML")
    return ASK_MEMBER


async def receive_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    term = (update.message.text or "").strip()

    # A bare number is treated as a Telegram ID, so you can grant access to
    # someone who isn't in the members table yet.
    if term.isdigit():
        member = await user_repository.get_by_chat_id(term)
        return await _ask_duration(update.message.reply_text, context, term, member)

    matches = await user_repository.search_by_name(term)
    if not matches:
        await update.message.reply_text(messages.MAKE_ADMIN_NO_MATCH)
        return ASK_MEMBER

    total = await user_repository.count_by_name(term)
    if total == 1:
        return await _ask_duration(update.message.reply_text, context, matches[0].chatId, matches[0])

    choices = messages.disambiguate([(m, m.chatId) for m in matches])

    await update.message.reply_text(
        messages.member_matches(term, len(matches), total),
        reply_markup=keyboards.member_pick_markup(choices),
    )
    return PICK_MEMBER


async def picked_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "pickadmin_cancel":
        return await cancel_make_admin(update, context)

    chat_id = query.data.replace("pickadmin_", "")
    member = await user_repository.get_by_chat_id(chat_id)
    return await _ask_duration(query.edit_message_text, context, chat_id, member)


async def _ask_duration(send, context, telegram_id, member=None):
    """Confirm who was picked, then ask for how long."""
    context.user_data["grant_target"] = str(telegram_id)
    name = messages.member_name(member, telegram_id)
    await send(
        messages.make_admin_ask_duration(name),
        reply_markup=keyboards.duration_markup(DURATION_PRESETS),
        parse_mode="HTML",
    )
    return ASK_DURATION


async def chose_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "dur_cancel":
        return await cancel_make_admin(update, context)
    if query.data == "dur_custom":
        await query.edit_message_text(messages.MAKE_ADMIN_ASK_DURATION, parse_mode="HTML")
        return ASK_DURATION

    minutes = int(query.data.replace("dur_", ""))
    return await _do_grant(query.edit_message_text, update, context, parse_duration(f"{minutes}m"))


async def typed_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = parse_duration(update.message.text)
    except TimeParseError as e:
        await update.message.reply_text(messages.admin_duration_rejected(str(e)), parse_mode="HTML")
        return ASK_DURATION
    return await _do_grant(update.message.reply_text, update, context, duration)


async def _do_grant(send, update, context, duration):
    telegram_id = context.user_data.get("grant_target")
    if not telegram_id:
        # The conversation lost its place, e.g. the bot restarted mid-flow.
        # Say so rather than leaving the admin looking at nothing.
        await send(messages.MENU_EXPIRED)
        return ConversationHandler.END

    try:
        until = await admin_service.grant(
            telegram_id, duration, granted_by=update.effective_user.id
        )
    except admin_service.AdminError as e:
        await send(messages.admin_grant_rejected(str(e)))
        return ConversationHandler.END
    except Exception:
        logger.exception("Could not grant admin access to %s", telegram_id)
        await send(messages.ADMIN_GRANT_SAVE_FAILED)
        return ConversationHandler.END

    member = await user_repository.get_by_chat_id(telegram_id)
    label = messages.member_label(member, telegram_id)

    try:
        await send(messages.admin_granted(label, until), parse_mode="HTML")
    except Exception:
        logger.exception("Access was granted but the confirmation could not be sent")
        await context.bot.send_message(
            chat_id=update.effective_user.id, text=messages.admin_granted(label, until)
        )

    # Give them the admin menu and let them know. Either can fail if they've
    # never messaged the bot; their access still works.
    await apply_admin_menu(context.bot, telegram_id)
    try:
        await context.bot.send_message(
            chat_id=telegram_id, text=messages.admin_granted_notice(until), parse_mode="HTML"
        )
    except Exception:
        logger.warning("Could not notify %s about their admin access", telegram_id)

    context.user_data.pop("grant_target", None)
    return ConversationHandler.END


async def cancel_make_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("grant_target", None)
    if update.callback_query:
        await update.callback_query.edit_message_text(messages.MAKE_ADMIN_CANCELLED)
    else:
        await update.message.reply_text(messages.MAKE_ADMIN_CANCELLED)
    return ConversationHandler.END


make_admin_handler = ConversationHandler(
    entry_points=[CommandHandler("make_admin", start_make_admin)],
    states={
        ASK_MEMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_member)],
        PICK_MEMBER: [CallbackQueryHandler(picked_member, pattern="^pickadmin_")],
        ASK_DURATION: [
            CallbackQueryHandler(chose_duration, pattern="^dur_"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, typed_duration),
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel_make_admin)],
    conversation_timeout=5 * 60,
)


# --- /admins -----------------------------------------------------------------
async def list_admins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not can_manage_admins(update.effective_user):
        await update.message.reply_text(messages.ADMIN_MANAGE_NOT_AUTHORIZED)
        return

    permanent_ids = admin_service.permanent_admin_ids()
    temporary_ids = admin_service.temporary_ids()

    all_ids = list(permanent_ids) + temporary_ids
    known = {u.chatId: u for u in await user_repository.get_many_by_chat_ids(all_ids)}
    labels = dict(messages.disambiguate([(known.get(str(i)), i) for i in all_ids]))

    permanent = [
        (labels[str(admin_id)], " (primary)" if index == 0 else "")
        for index, admin_id in enumerate(permanent_ids)
    ]
    temporary = [
        (labels[str(admin_id)], f" — {format_duration_left(admin_service.expires_at(admin_id))}")
        for admin_id in temporary_ids
    ]

    await update.message.reply_text(
        messages.admins_overview(permanent, temporary), parse_mode="HTML"
    )


# --- /revoke_admin -----------------------------------------------------------
async def start_revoke_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not can_manage_admins(update.effective_user):
        await update.message.reply_text(messages.ADMIN_MANAGE_NOT_AUTHORIZED)
        return

    temporary_ids = admin_service.temporary_ids()
    if not temporary_ids:
        await update.message.reply_text(messages.REVOKE_ADMIN_NONE)
        return

    known = {u.chatId: u for u in await user_repository.get_many_by_chat_ids(temporary_ids)}
    entries = [
        (admin_id, f"{label} ({format_duration_left(admin_service.expires_at(admin_id))})")
        for admin_id, label in messages.disambiguate(
            [(known.get(str(i)), i) for i in temporary_ids]
        )
    ]

    await update.message.reply_text(
        messages.REVOKE_ADMIN_ASK, reply_markup=keyboards.revoke_admin_markup(entries)
    )


async def confirm_revoke_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not can_manage_admins(update.effective_user):
        return
    if query.data == "revokeadmin_cancel":
        await query.edit_message_text(messages.MAKE_ADMIN_CANCELLED)
        return

    telegram_id = query.data.replace("revokeadmin_", "")
    try:
        had_grant = await admin_service.revoke(telegram_id, revoked_by=update.effective_user.id)
    except admin_service.AdminError as e:
        await query.edit_message_text(messages.admin_grant_rejected(str(e)))
        return
    except Exception:
        logger.exception("Could not revoke admin access for %s", telegram_id)
        await query.edit_message_text(messages.ADMIN_GRANT_SAVE_FAILED)
        return

    if not had_grant:
        await query.edit_message_text(messages.REVOKE_ADMIN_GONE)
        return

    member = await user_repository.get_by_chat_id(telegram_id)
    await query.edit_message_text(
        messages.admin_revoked(messages.member_label(member, telegram_id)), parse_mode="HTML"
    )

    await apply_member_menu(context.bot, telegram_id)
    try:
        await context.bot.send_message(chat_id=telegram_id, text=messages.ADMIN_REVOKED_NOTICE)
    except Exception:
        logger.warning("Could not tell %s their admin access ended", telegram_id)


admins_handler = CommandHandler("admins", list_admins)
revoke_admin_handler = CommandHandler("revoke_admin", start_revoke_admin)
revoke_admin_callback_handler = CallbackQueryHandler(confirm_revoke_admin, pattern="^revokeadmin_")
