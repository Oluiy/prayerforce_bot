"""User flow: /take_quiz -> timed multiple-choice questions -> score saved."""
import datetime
import random

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler

import messages
from config.constants import QUESTION_TIME_LIMIT_SECONDS
from repositories import user_repository
from services import quiz_service

QUIZ_QUESTION = 1


def _cancel_timer(context: ContextTypes.DEFAULT_TYPE):
    timer = context.user_data.get("question_timer")
    if timer:
        timer.schedule_removal()
        context.user_data["question_timer"] = None


async def start_quiz_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    quiz = await quiz_service.find_open_quiz()

    if not quiz:
        await update.message.reply_text(messages.NO_ACTIVE_QUIZ)
        return ConversationHandler.END

    if not quiz.questions:
        await update.message.reply_text(messages.QUIZ_HAS_NO_QUESTIONS)
        return ConversationHandler.END

    db_user = await user_repository.get_or_create(user)
    existing_score = await quiz_service.get_existing_score(db_user.id, quiz.id)
    if existing_score:
        await update.message.reply_text(messages.already_taken(existing_score.score))
        return ConversationHandler.END

    questions = quiz_service.pick_questions_for_user(quiz.questions)

    context.user_data["quiz_id"] = quiz.id
    context.user_data["questions"] = questions
    context.user_data["current_index"] = 0
    context.user_data["score"] = 0
    context.user_data["user_id"] = str(user.id)
    context.user_data["quiz_started_at"] = datetime.datetime.now().timestamp()

    await update.message.reply_text(messages.quiz_starting(quiz.type, len(questions)))
    return await ask_question(update, context)


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    if not chat_id:
        chat_id = update.effective_chat.id

    index = context.user_data["current_index"]
    questions = context.user_data["questions"]

    if index >= len(questions):
        return await finish_quiz(update, context, chat_id=chat_id)

    question = questions[index]
    options = question.options
    random.shuffle(options)

    # One option per row so long answers stay readable on every device.
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton(opt.text, callback_data=f"ans_{opt.id}")] for opt in options]
    )
    base_text = messages.question_header(index, len(questions), question.text)

    _cancel_timer(context)
    context.user_data["timer_for_index"] = index

    user_id_val = context.user_data.get("user_id")
    if not user_id_val and update and update.effective_user:
        user_id_val = update.effective_user.id

    # Show the previous answer's result above the new question, once.
    prev_result = context.user_data.get("prev_result", "")
    if prev_result:
        base_text = f"{prev_result}\n\n{base_text}"
        context.user_data["prev_result"] = ""
    text = messages.with_full_timer(base_text)

    # Re-use the existing message where possible instead of sending a new one each time.
    last_msg_id = context.user_data.get("quiz_msg_id")
    msg = None
    if last_msg_id and update and getattr(update, "callback_query", None):
        try:
            msg = await context.bot.edit_message_text(
                chat_id=chat_id, message_id=last_msg_id, text=text, reply_markup=reply_markup
            )
        except Exception:
            pass

    if not msg:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup)
        context.user_data["quiz_msg_id"] = msg.message_id

    # Tick once a second to update the countdown.
    context.user_data["question_timer"] = context.job_queue.run_repeating(
        countdown_job,
        interval=1,
        first=1,
        data={
            "chat_id": chat_id,
            "message_id": msg.message_id,
            "user_id": user_id_val,
            "base_text": base_text,
            "reply_markup": reply_markup,
            "time_left": QUESTION_TIME_LIMIT_SECONDS,
            "index": index,
        },
        chat_id=chat_id,
        user_id=int(user_id_val) if user_id_val else None,
    )

    return QUIZ_QUESTION


async def countdown_job(context: ContextTypes.DEFAULT_TYPE):
    job = context.job
    data = job.data
    chat_id = data["chat_id"]
    message_id = data["message_id"]
    time_left = data["time_left"] - 1
    data["time_left"] = time_left

    if context.user_data is None:
        job.schedule_removal()
        return

    # Stop if the user has already moved past this question.
    if context.user_data.get("current_index", 0) != data["index"]:
        job.schedule_removal()
        return

    if time_left > 0:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=messages.with_time_left(data["base_text"], time_left),
                reply_markup=data["reply_markup"],
            )
        except Exception:
            pass  # same text or rate limited
        return

    job.schedule_removal()
    context.user_data["question_timer"] = None

    try:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=messages.times_up(data["base_text"]),
            reply_markup=None,
        )
    except Exception:
        pass

    context.user_data["current_index"] += 1
    if context.user_data["current_index"] >= len(context.user_data.get("questions", [])):
        await finish_quiz(None, context, chat_id=chat_id)
    else:
        await ask_question(None, context, chat_id=chat_id)


async def handle_user_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_answer_id = query.data.replace("ans_", "")
    _cancel_timer(context)

    index = context.user_data.get("current_index", 0)
    questions = context.user_data.get("questions", [])
    if index >= len(questions):
        return await finish_quiz(update, context)

    question = questions[index]
    correct_option = next((opt for opt in question.options if opt.isCorrect), None)
    selected_option = next((opt for opt in question.options if str(opt.id) == user_answer_id), None)

    if correct_option and selected_option and str(selected_option.id) == str(correct_option.id):
        context.user_data["score"] += 1
        response_text = messages.answer_correct(question.text, selected_option.text)
    else:
        response_text = messages.answer_wrong(question.text, correct_option.text if correct_option else None)

    try:
        await query.edit_message_text(text=response_text, reply_markup=None)
    except Exception:
        pass

    context.user_data["current_index"] += 1
    return await ask_question(update, context)


async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, chat_id=None):
    if not chat_id and update:
        chat_id = update.effective_chat.id

    score = context.user_data.get("score", 0)
    quiz_id = context.user_data.get("quiz_id")
    user_id = context.user_data.get("user_id")
    quiz_started_at = context.user_data.get("quiz_started_at")
    elapsed_seconds = 0
    if quiz_started_at:
        elapsed_seconds = max(1, int(datetime.datetime.now().timestamp() - float(quiz_started_at)))

    if not user_id and update:
        user_id = str(update.effective_user.id)

    if user_id:
        await quiz_service.record_score(user_id, quiz_id, score, elapsed_seconds)

    msg = messages.quiz_finished(score, len(context.user_data.get("questions", [])), elapsed_seconds)
    if update and update.callback_query:
        await update.callback_query.edit_message_text(text=msg, reply_markup=None)
    elif update and update.message:
        await update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove())
    else:
        await context.bot.send_message(chat_id=chat_id, text=msg, reply_markup=ReplyKeyboardRemove())

    timer = context.user_data.get("question_timer")
    if timer:
        timer.schedule_removal()

    return ConversationHandler.END


async def cancel_quiz_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(messages.QUIZ_CANCELLED, reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


quiz_user_handler = ConversationHandler(
    entry_points=[CommandHandler("take_quiz", start_quiz_user)],
    states={QUIZ_QUESTION: [CallbackQueryHandler(handle_user_answer, pattern="^ans_")]},
    fallbacks=[CommandHandler("cancel", cancel_quiz_user)],
)
