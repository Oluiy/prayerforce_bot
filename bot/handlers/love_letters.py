"""Admin-only love letters: write this week's set and send them out.

One conversation holds the whole flow so the buttons and the typed steps share
the same state. Only admins can start it; the commands are also absent from
members' menus (see messages.ADMIN_COMMANDS and handlers/menu.py).
"""
import logging

import keyboards
import messages
from repositories import love_letter_repository, user_repository
from services import love_letter_service
from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from utils.auth import is_admin

logger = logging.getLogger(__name__)

HUB, ADD_TEXT, PICK_MEMBER, PICK_LETTER = range(40, 44)


async def _guard(update: Update) -> bool:
    """True if the sender is an admin. Tells everyone else why nothing happened."""
    if is_admin(update.effective_user):
        return True

    if update.callback_query:
        await update.callback_query.answer(
            messages.LOVE_LETTERS_NOT_AUTHORIZED, show_alert=True
        )
    elif update.message:
        await update.message.reply_text(messages.LOVE_LETTERS_NOT_AUTHORIZED)
    return False


async def _hub_view():
    """(text, markup) for the hub, so it can be sent or edited."""
    week, letters, members, served = await love_letter_service.overview()
    return (
        messages.love_letters_hub(week, len(letters), len(members), served),
        keyboards.love_letters_hub_markup(len(letters)),
    )


async def _ask_letter(send, context, member):
    """Show this week's letters and remember who they're for."""
    letters = await love_letter_service.letters_for_week()
    if not letters:
        await send(
            messages.love_letters_list(letters),
            reply_markup=keyboards.love_letters_back_markup(),
            parse_mode="HTML",
        )
        return HUB

    context.user_data["ll_target"] = member.chatId
    await send(
        messages.love_letters_ask_letter(
            messages.member_label(member, member.chatId), len(letters)
        ),
        reply_markup=keyboards.love_letters_pick_markup(letters),
        parse_mode="HTML",
    )
    return PICK_LETTER


# --- Entry points ------------------------------------------------------------
async def show_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END

    text, markup = await _hub_view()
    await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")
    return HUB


async def start_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END

    await update.message.reply_text(messages.LOVE_LETTERS_ASK_TEXT, parse_mode="HTML")
    return ADD_TEXT


# --- Hub buttons -------------------------------------------------------------
async def hub_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await _guard(update):
        return ConversationHandler.END

    data = query.data

    if data == "ll_cancel":
        await query.edit_message_text(messages.LOVE_LETTERS_CANCELLED)
        return ConversationHandler.END

    if data == "ll_home":
        text, markup = await _hub_view()
        await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        return HUB

    if data == "ll_list":
        letters = await love_letter_service.letters_for_week()
        await query.edit_message_text(
            messages.love_letters_list(letters),
            reply_markup=keyboards.love_letters_back_markup(),
            parse_mode="HTML",
        )
        return HUB

    if data == "ll_add":
        await query.edit_message_text(messages.LOVE_LETTERS_ASK_TEXT, parse_mode="HTML")
        return ADD_TEXT

    if data == "ll_send_one":
        context.user_data.pop("ll_target", None)
        await query.edit_message_text(messages.LOVE_LETTERS_ASK_MEMBER)
        return PICK_MEMBER

    if data == "ll_send_all":
        week, letters, members, served = await love_letter_service.overview()
        if not letters:
            await query.edit_message_text(
                messages.love_letters_list(letters),
                reply_markup=keyboards.love_letters_back_markup(),
                parse_mode="HTML",
            )
            return HUB
        remaining = max(0, len(members) - served)
        await query.edit_message_text(
            messages.love_letters_preview(len(letters), remaining),
            reply_markup=keyboards.love_letters_confirm_markup(),
            parse_mode="HTML",
        )
        return HUB

    if data == "ll_go_all":
        try:
            report = await love_letter_service.send_weekly(context.bot)
        except love_letter_service.LoveLetterError as e:
            await query.edit_message_text(
                messages.love_letters_rejected(str(e)), parse_mode="HTML"
            )
            return HUB
        except Exception:
            logger.exception("Love letter send failed")
            await query.edit_message_text(messages.LOVE_LETTERS_SEND_FAILED)
            return ConversationHandler.END

        await query.edit_message_text(
            messages.love_letters_report(report), parse_mode="HTML"
        )
        return ConversationHandler.END

    # Unknown button, show the hub again rather than doing nothing.
    text, markup = await _hub_view()
    await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    return HUB


# --- Writing a letter --------------------------------------------------------
async def receive_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END

    try:
        _, count = await love_letter_service.add_letter(update.message.text)
    except love_letter_service.LoveLetterError as e:
        await update.message.reply_text(
            messages.love_letters_rejected(str(e)), parse_mode="HTML"
        )
        return ADD_TEXT
    except Exception:
        logger.exception("Could not save a love letter")
        await update.message.reply_text(messages.LOVE_LETTERS_SAVE_FAILED)
        return ADD_TEXT

    await update.message.reply_text(
        messages.love_letter_saved(count, love_letter_service.week_key()),
        parse_mode="HTML",
    )
    return ADD_TEXT


# --- Sending to one member ---------------------------------------------------
async def receive_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _guard(update):
        return ConversationHandler.END

    term = (update.message.text or "").strip()
    if not term:
        await update.message.reply_text(messages.LOVE_LETTERS_ASK_MEMBER)
        return PICK_MEMBER

    # A bare number is a Telegram ID, so admins can reach someone not in the
    # members table by name yet.
    if term.isdigit():
        member = await user_repository.get_by_chat_id(term)
        if not member:
            await update.message.reply_text(messages.LOVE_LETTERS_NO_MATCH)
            return PICK_MEMBER
        return await _ask_letter(update.message.reply_text, context, member)

    matches = await user_repository.search_by_name(term)
    total = await user_repository.count_by_name(term)
    if not matches:
        await update.message.reply_text(messages.LOVE_LETTERS_NO_MATCH)
        return PICK_MEMBER
    if total == 1:
        return await _ask_letter(update.message.reply_text, context, matches[0])

    choices = messages.disambiguate([(m, m.chatId) for m in matches])
    await update.message.reply_text(
        messages.love_letters_choose_member(term, len(matches), total),
        reply_markup=keyboards.love_letters_member_markup(choices),
        parse_mode="HTML",
    )
    return PICK_MEMBER


async def picked_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await _guard(update):
        return ConversationHandler.END

    if query.data == "ll_cancel":
        return await close(update, context)

    chat_id = query.data.replace("llmem_", "")
    member = await user_repository.get_by_chat_id(chat_id)
    if not member:
        await query.edit_message_text(messages.LOVE_LETTERS_MEMBER_GONE)
        return ConversationHandler.END

    return await _ask_letter(query.edit_message_text, context, member)


# --- Sending the chosen letter ----------------------------------------------
async def send_direct_letter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await _guard(update):
        return ConversationHandler.END

    if query.data == "ll_cancel":
        return await close(update, context)

    chat_id = context.user_data.get("ll_target")
    member = await user_repository.get_by_chat_id(chat_id) if chat_id else None
    if not member:
        await query.edit_message_text(messages.LOVE_LETTERS_MEMBER_GONE)
        return ConversationHandler.END

    letters = await love_letter_service.letters_for_week()
    if query.data == "ll_random":
        try:
            letter = await love_letter_service.pick_random_letter(letters)
        except love_letter_service.LoveLetterError as e:
            await query.edit_message_text(
                messages.love_letters_rejected(str(e)), parse_mode="HTML"
            )
            return ConversationHandler.END
    else:
        letter_id = query.data.replace("llletter_", "")
        letter = await love_letter_repository.get(letter_id)
        if not letter:
            await query.edit_message_text(messages.LOVE_LETTERS_LETTER_GONE)
            return ConversationHandler.END

    try:
        await love_letter_service.send_direct(context.bot, member, letter)
    except Exception:
        logger.exception("Could not send a direct love letter to %s", member.chatId)
        await query.edit_message_text(messages.LOVE_LETTERS_SEND_FAILED)
        return ConversationHandler.END

    context.user_data.pop("ll_target", None)
    await query.edit_message_text(
        messages.love_letters_direct_sent(
            messages.member_name(member, member.chatId), letter.body
        ),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("ll_target", None)

    if update.callback_query:
        await update.callback_query.edit_message_text(messages.LOVE_LETTERS_CANCELLED)
    else:
        await update.message.reply_text(messages.LOVE_LETTERS_CANCELLED)
    return ConversationHandler.END


love_letters_handler = ConversationHandler(
    entry_points=[
        CommandHandler("love_letters", show_hub),
        CommandHandler("add_letter", start_add),
    ],
    states={
        HUB: [CallbackQueryHandler(hub_action, pattern="^ll_")],
        ADD_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_letter)],
        PICK_MEMBER: [
            CallbackQueryHandler(picked_member, pattern="^(llmem_|ll_cancel)"),
            MessageHandler(filters.TEXT & ~filters.COMMAND, receive_member),
        ],
        PICK_LETTER: [
            CallbackQueryHandler(
                send_direct_letter, pattern="^(llletter_|ll_random|ll_cancel)"
            )
        ],
    },
    fallbacks=[CommandHandler("cancel", close)],
    # /love_letters should reopen the hub from any step.
    allow_reentry=True,
    conversation_timeout=15 * 60,
)
