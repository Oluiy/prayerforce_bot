"""Choosing when a quiz opens and closes, plus /end_quiz and /quizzes.

Times belong to the quiz, not to the app: whoever creates a quiz picks its
window, and it can be closed early at any time.
"""
import datetime
import logging

from telegram import Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

import keyboards
import messages
import notifications
from config.constants import DEFAULT_QUIZ_CLOSE_TIME, DEFAULT_QUIZ_OPEN_TIME
from services import quiz_service
from utils.auth import is_admin
from utils.dates import TimeParseError, format_moment, local_now, parse_when, to_local, to_utc

logger = logging.getLogger(__name__)

# Offset so these don't collide with WAITING_NOTES in handlers/quiz_admin.py.
CHOOSING_TYPE, CHOOSING_OPEN, CHOOSING_CLOSE = range(10, 13)


# --- Building the preset buttons ---------------------------------------------
def _at_time(day: datetime.datetime, when: datetime.time) -> datetime.datetime:
    return day.replace(hour=when.hour, minute=when.minute, second=0, microsecond=0)


def open_presets(now=None):
    """Offer "now", and the usual opening time today (if still ahead) and tomorrow."""
    now = now or local_now()
    default = DEFAULT_QUIZ_OPEN_TIME
    presets = [("Open now", to_utc(now))]

    today = _at_time(now, default)
    if today > now:
        presets.append((f"Today at {format_moment(to_utc(today), now=now).split('at ')[-1]}", to_utc(today)))
    tomorrow = _at_time(now + datetime.timedelta(days=1), default)
    presets.append((f"Tomorrow at {format_moment(to_utc(tomorrow), now=now).split('at ')[-1]}", to_utc(tomorrow)))
    return presets


def close_presets(opens_at, now=None):
    """Offer the usual closing time after opening, plus a day and a week."""
    now = now or local_now()
    default = DEFAULT_QUIZ_CLOSE_TIME
    opens_local = to_local(opens_at)

    same_day = _at_time(opens_local, default)
    if same_day <= opens_local:
        same_day += datetime.timedelta(days=1)

    same_day_label = format_moment(to_utc(same_day), now=now)
    return [
        (same_day_label[0].upper() + same_day_label[1:], to_utc(same_day)),
        ("24 hours after opening", opens_at + datetime.timedelta(hours=24)),
        ("1 week after opening", opens_at + datetime.timedelta(days=7)),
    ]


def _store(context, key, presets):
    context.user_data[key] = [moment for _, moment in presets]
    return [(label, f"{key}_{index}") for index, (label, _) in enumerate(presets)]


# --- The scheduling conversation ---------------------------------------------
async def ask_quiz_type(message, context, quiz_id, question_count):
    """Entry point used right after a quiz is generated."""
    context.user_data["scheduling_quiz_id"] = quiz_id
    context.user_data["scheduling_question_count"] = question_count
    await message.reply_text(
        f"{messages.quiz_generated(question_count)}\n\nWhat kind of quiz is this?",
        reply_markup=keyboards.quiz_type_markup(),
    )
    return CHOOSING_TYPE


async def chose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "sched_cancel":
        return await cancel_scheduling(update, context)

    quiz_type = query.data.replace("qtype_", "")
    quiz_id = context.user_data.get("scheduling_quiz_id")
    if quiz_id:
        await quiz_service.set_type(quiz_id, quiz_type)
    context.user_data["scheduling_type"] = quiz_type

    presets = _store(context, "sched_open", open_presets())
    await query.edit_message_text(
        messages.SCHEDULE_ASK_OPEN, reply_markup=keyboards.schedule_markup(presets), parse_mode="Markdown"
    )
    return CHOOSING_OPEN


async def chose_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "sched_cancel":
        return await cancel_scheduling(update, context)
    if query.data == "sched_custom":
        await query.edit_message_text(messages.SCHEDULE_ASK_OPEN, parse_mode="Markdown")
        return CHOOSING_OPEN

    index = int(query.data.rsplit("_", 1)[1])
    opens_at = context.user_data["sched_open"][index]
    return await _ask_close(query.edit_message_text, context, opens_at)


async def typed_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        opens_at = parse_when(update.message.text)
    except TimeParseError as e:
        await update.message.reply_text(messages.schedule_bad_time(str(e)), parse_mode="Markdown")
        return CHOOSING_OPEN
    return await _ask_close(update.message.reply_text, context, opens_at)


async def _ask_close(send, context, opens_at):
    context.user_data["scheduling_opens_at"] = opens_at
    presets = _store(context, "sched_close", close_presets(opens_at))
    await send(
        messages.SCHEDULE_ASK_CLOSE, reply_markup=keyboards.schedule_markup(presets), parse_mode="Markdown"
    )
    return CHOOSING_CLOSE


async def chose_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "sched_cancel":
        return await cancel_scheduling(update, context)
    if query.data == "sched_custom":
        await query.edit_message_text(messages.SCHEDULE_ASK_CLOSE, parse_mode="Markdown")
        return CHOOSING_CLOSE

    index = int(query.data.rsplit("_", 1)[1])
    closes_at = context.user_data["sched_close"][index]
    return await _finish(query.edit_message_text, update, context, closes_at)


async def typed_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        closes_at = parse_when(update.message.text)
    except TimeParseError as e:
        await update.message.reply_text(messages.schedule_bad_time(str(e)), parse_mode="Markdown")
        return CHOOSING_CLOSE
    return await _finish(update.message.reply_text, update, context, closes_at)


async def _finish(send, update, context, closes_at):
    opens_at = context.user_data.get("scheduling_opens_at")
    quiz_id = context.user_data.get("scheduling_quiz_id")
    question_count = context.user_data.get("scheduling_question_count", 0)

    if opens_at and closes_at <= opens_at:
        await send(messages.SCHEDULE_CLOSE_BEFORE_OPEN)
        return CHOOSING_CLOSE

    now = to_utc(local_now())
    if closes_at <= now:
        await send(messages.SCHEDULE_IN_THE_PAST)
        return CHOOSING_CLOSE

    try:
        await quiz_service.set_schedule(quiz_id, opens_at, closes_at)

        # "Open now" shouldn't wait for the next sweep.
        opened_now = opens_at <= now
        if opened_now:
            quiz = await quiz_service.open_now(quiz_id)
            await notifications.announce_quiz_open(context.bot, quiz)
    except Exception:
        logger.exception("Could not schedule quiz %s", quiz_id)
        await send(messages.SCHEDULE_SAVE_FAILED)
        return ConversationHandler.END

    await send(
        messages.schedule_confirmed(question_count, opens_at, closes_at, opened_now),
        parse_mode="Markdown",
    )
    _clear(context)
    return ConversationHandler.END


async def cancel_scheduling(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _clear(context)
    if update.callback_query:
        await update.callback_query.edit_message_text(messages.SCHEDULE_CANCELLED)
    else:
        await update.message.reply_text(messages.SCHEDULE_CANCELLED)
    return ConversationHandler.END


def _clear(context):
    for key in (
        "scheduling_quiz_id", "scheduling_question_count", "scheduling_type",
        "scheduling_opens_at", "sched_open", "sched_close",
    ):
        context.user_data.pop(key, None)


SCHEDULE_STATES = {
    CHOOSING_TYPE: [CallbackQueryHandler(chose_type, pattern="^(qtype_|sched_cancel)")],
    CHOOSING_OPEN: [
        CallbackQueryHandler(chose_open, pattern="^(sched_open_|sched_custom|sched_cancel)"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, typed_open),
    ],
    CHOOSING_CLOSE: [
        CallbackQueryHandler(chose_close, pattern="^(sched_close_|sched_custom|sched_cancel)"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, typed_close),
    ],
}


# --- /quizzes ----------------------------------------------------------------
async def list_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text(messages.QUIZZES_NOT_AUTHORIZED)
        return

    open_quizzes = await quiz_service.list_open()
    scheduled = await quiz_service.list_scheduled()
    closed = await quiz_service.list_recently_closed(limit=3)

    if not (open_quizzes or scheduled or closed):
        await update.message.reply_text(messages.QUIZZES_NONE)
        return

    await update.message.reply_text(
        messages.quizzes_overview(open_quizzes, scheduled, closed), parse_mode="Markdown"
    )


# --- /end_quiz ---------------------------------------------------------------
async def start_end_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text(messages.END_QUIZ_NOT_AUTHORIZED)
        return

    open_quizzes = await quiz_service.list_open()
    if not open_quizzes:
        await update.message.reply_text(messages.END_QUIZ_NONE_OPEN)
        return

    await update.message.reply_text(
        messages.END_QUIZ_ASK, reply_markup=keyboards.end_quiz_markup(open_quizzes)
    )


async def confirm_end_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user):
        return
    if query.data == "endquiz_cancel":
        await query.edit_message_text(messages.SETTINGS_CANCELLED)
        return

    quiz_id = query.data.replace("endquiz_", "")
    result = await quiz_service.close_quiz_by_id(quiz_id, closed_early_by=update.effective_user.id)
    if not result:
        await query.edit_message_text(messages.END_QUIZ_GONE)
        return

    quiz, scores = result
    await query.edit_message_text(messages.end_quiz_done(quiz, len(scores)), parse_mode="Markdown")
    await notifications.announce_quiz_closed(context.bot, quiz, scores)


quizzes_handler = CommandHandler("quizzes", list_quizzes)
end_quiz_handler = CommandHandler("end_quiz", start_end_quiz)
end_quiz_callback_handler = CallbackQueryHandler(confirm_end_quiz, pattern="^endquiz_")
