"""Quiz business rules: creating, opening, closing, scoring and ranking quizzes.

This module knows nothing about Telegram. Handlers and jobs call it and
decide how to present the results.
"""
import datetime
import logging
import random

from config.constants import (
    LEADERBOARD_SIZE,
    LEADERBOARD_VISIBLE_DAYS,
    MONTHLY_LEADERBOARD_SIZE,
    MONTHLY_RECAP_LOOKBACK_DAYS,
    MONTHLY_RECAP_QUESTIONS,
    QUESTIONS_PER_USER,
)
from repositories import quiz_repository, score_repository, user_repository
from utils.dates import utc_now

logger = logging.getLogger(__name__)

NO_TIME_RECORDED = 10**9  # sorts entries without a time to the bottom of ties


# --- Creating quizzes --------------------------------------------------------
async def save_generated_quiz(questions_data, quiz_type="daily"):
    """Store AI-generated questions as a new quiz. Rolls back the quiz if any question fails."""
    quiz = await quiz_repository.create(
        quiz_type=quiz_type, week_start=datetime.datetime.now(), is_active=True
    )
    try:
        for q in questions_data:
            if "question" not in q or "options" not in q or "correct_answer" not in q:
                raise ValueError("Invalid question format from AI")
            options = [(text, text == q["correct_answer"]) for text in q["options"]]
            await quiz_repository.add_question(quiz.id, q["question"], options)
    except Exception:
        logger.exception("Error inserting questions. Rolling back quiz %s", quiz.id)
        await quiz_repository.delete(quiz.id)
        raise
    return quiz


async def create_monthly_recap(today):
    """Build a recap quiz from the past month's weekly questions.

    Returns the number of questions in the recap, or None if there were none.
    """
    await quiz_repository.close_all_active("weekly")

    since = today - datetime.timedelta(days=MONTHLY_RECAP_LOOKBACK_DAYS)
    past_quizzes = await quiz_repository.find_since_with_questions("weekly", since)
    all_questions = [q for quiz in past_quizzes for q in quiz.questions]
    if not all_questions:
        return None

    selected = random.sample(all_questions, min(len(all_questions), MONTHLY_RECAP_QUESTIONS))
    recap = await quiz_repository.create(quiz_type="monthly", week_start=today, is_active=True)
    for old_q in selected:
        options = [(opt.text, opt.isCorrect) for opt in old_q.options]
        await quiz_repository.add_question(recap.id, f"[Monthly Recap] {old_q.text}", options)
    return len(selected)


# --- Opening & closing -------------------------------------------------------
async def open_weekly_quiz():
    """Open the latest pending weekly quiz, unless a monthly recap is running."""
    if await quiz_repository.find_active("monthly", order_by="weekStart"):
        logger.info("Monthly quiz is active, skipping weekly quiz open.")
        return None
    return await _open_pending("weekly", order_by="weekStart")


async def open_daily_quiz():
    """Close any running monthly recap, then open the latest pending daily quiz."""
    active_monthly = await quiz_repository.find_active("monthly", order_by="weekStart")
    if active_monthly:
        await quiz_repository.deactivate(active_monthly.id)
    return await _open_pending("daily", order_by="createdAt")


async def _open_pending(quiz_type, order_by):
    quiz = await quiz_repository.find_pending(quiz_type, order_by=order_by)
    if quiz:
        logger.info("Opening quiz %s", quiz.id)
        await quiz_repository.activate(quiz.id)
    return quiz


async def close_active_quiz(quiz_type, order_by):
    """Close the active quiz of this type.

    Returns (quiz, scores ordered highest first), or (None, []) if nothing was open.
    """
    quiz = await quiz_repository.find_active(quiz_type, order_by=order_by)
    if not quiz:
        return None, []
    scores = await score_repository.list_for_quiz(quiz.id, highest_first=True)
    await quiz_repository.close(quiz.id)
    logger.info("Quiz '%s' successfully closed.", quiz.id)
    return quiz, scores


async def add_scores_to_monthly_totals(scores, now):
    month_year = now.strftime("%Y-%m")
    for entry in scores:
        await score_repository.add_to_cumulative(
            entry.userId, month_year, entry.score, entry.timeTakenSeconds
        )
        logger.info("Updated cumulative score for %s", entry.user.firstName)


# --- Taking a quiz -----------------------------------------------------------
async def find_open_quiz():
    return await quiz_repository.find_open_with_questions()


async def get_existing_score(user_id, quiz_id):
    return await score_repository.get_user_score(user_id, quiz_id)


def pick_questions_for_user(questions):
    """Random subset of the quiz's question pool for one user."""
    return random.sample(questions, min(len(questions), QUESTIONS_PER_USER))


async def record_score(chat_id, quiz_id, score, time_taken_seconds):
    user = await user_repository.get_by_chat_id(chat_id)
    if user:
        await score_repository.create_user_score(user.id, quiz_id, score, time_taken_seconds)


# --- Leaderboards ------------------------------------------------------------
def _rank(entries, score_field):
    """Highest score first; on a tie, the faster time wins."""
    def key(entry):
        time_taken = entry.timeTakenSeconds if entry.timeTakenSeconds is not None else NO_TIME_RECORDED
        return (-getattr(entry, score_field), time_taken)
    return sorted(entries, key=key)


async def get_leaderboard(quiz_id=None):
    """Top scores for a quiz.

    With a quiz_id, use that quiz. Otherwise use the newest started quiz,
    hiding it once it has been closed for LEADERBOARD_VISIBLE_DAYS.

    Returns (title_suffix, top_entries), or None if there's nothing to show.
    """
    if quiz_id:
        quiz = await quiz_repository.get(quiz_id)
        if not quiz:
            return None
        title_suffix = "(Final)" if quiz.isClosed and not quiz.isActive else "(Live)"
    else:
        quiz = await quiz_repository.find_latest_started()
        if not quiz:
            return None
        if quiz.isActive:
            title_suffix = "(Live)"
        else:
            if (utc_now() - quiz.weekStart).days >= LEADERBOARD_VISIBLE_DAYS:
                return None
            title_suffix = "(Final)"

    scores = await score_repository.list_for_quiz(quiz.id)
    top = _rank(scores, "score")[:LEADERBOARD_SIZE]
    if not top:
        return None
    return title_suffix, top


async def get_monthly_leaderboard(month_year):
    entries = await score_repository.list_cumulative_for_month(month_year)
    # Original ordering treated a 0 total time like "no time" for tie-breaks.
    ranked = sorted(
        entries,
        key=lambda e: (-e.cumulativeScore, e.timeTakenSeconds if e.timeTakenSeconds else NO_TIME_RECORDED),
    )
    return ranked[:MONTHLY_LEADERBOARD_SIZE]
