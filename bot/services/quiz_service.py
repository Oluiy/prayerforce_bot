"""Quiz business rules: creating, scheduling, closing, scoring and ranking.

This module knows nothing about Telegram. Handlers and jobs call it and
decide how to present the results.

Each quiz carries its own `opensAt` and `closesAt`, set by the admin who
creates it. `run_schedule_sweep` is what actually opens and closes them.
"""
import datetime
import logging
import random

from config.constants import (
    LEADERBOARD_VISIBLE_DAYS,
    MONTHLY_LEADERBOARD_SIZE,
    MONTHLY_RECAP_LOOKBACK_DAYS,
    MONTHLY_RECAP_QUESTIONS,
)
from repositories import quiz_repository, score_repository, user_repository
from utils.dates import utc_now

from services import settings_service

logger = logging.getLogger(__name__)

NO_TIME_RECORDED = 10**9  # sorts entries without a time to the bottom of ties


# --- Creating quizzes --------------------------------------------------------
async def save_generated_quiz(questions_data, quiz_type="daily", opens_at=None, closes_at=None):
    """Store AI-generated questions as a new quiz.

    The quiz starts closed; the sweep opens it when `opens_at` arrives.
    Rolls the whole quiz back if any question fails to save.
    """
    quiz = await quiz_repository.create(
        quiz_type=quiz_type,
        week_start=datetime.datetime.now(),
        is_active=False,
        opens_at=opens_at,
        closes_at=closes_at,
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


async def set_schedule(quiz_id, opens_at, closes_at):
    return await quiz_repository.set_schedule(quiz_id, opens_at, closes_at)


async def set_type(quiz_id, quiz_type):
    return await quiz_repository.set_type(quiz_id, quiz_type)


async def open_now(quiz_id):
    """Open a quiz straight away, so the admin doesn't wait for the next sweep."""
    return await quiz_repository.activate(quiz_id)


async def create_monthly_recap(today, opens_at=None, closes_at=None):
    """Build a recap quiz from the past month's weekly questions.

    Returns (quiz, question_count), or None if there were no questions to reuse.
    """
    await quiz_repository.close_all_active("weekly")

    since = today - datetime.timedelta(days=MONTHLY_RECAP_LOOKBACK_DAYS)
    past_quizzes = await quiz_repository.find_since_with_questions("weekly", since)
    all_questions = [q for quiz in past_quizzes for q in quiz.questions]
    if not all_questions:
        return None

    selected = random.sample(all_questions, min(len(all_questions), MONTHLY_RECAP_QUESTIONS))
    recap = await quiz_repository.create(
        quiz_type="monthly",
        week_start=today,
        is_active=opens_at is None,  # with no schedule it opens straight away
        opens_at=opens_at,
        closes_at=closes_at,
    )
    for old_q in selected:
        options = [(opt.text, opt.isCorrect) for opt in old_q.options]
        await quiz_repository.add_question(recap.id, f"[Monthly Recap] {old_q.text}", options)
    return recap, len(selected)


# --- The schedule sweep ------------------------------------------------------
class SweepResult:
    """What a sweep did, so the caller can announce it."""

    def __init__(self):
        self.opened = []  # quizzes that just opened
        self.closed = []  # (quiz, scores) pairs for quizzes that just closed

    @property
    def changed(self) -> bool:
        return bool(self.opened or self.closed)


async def run_schedule_sweep(now=None) -> SweepResult:
    """Open and close quizzes whose times have arrived.

    Safe to run as often as you like, and safe to miss runs: it works from
    the stored times, so a restart or downtime just means the next sweep
    catches up.
    """
    now = now or utc_now()
    result = SweepResult()

    for quiz in await quiz_repository.find_due_to_open(now):
        await quiz_repository.activate(quiz.id)
        overdue = quiz.closesAt is not None and quiz.closesAt <= now
        if overdue:
            # The whole window passed while we weren't running. Don't announce
            # an opening nobody can act on; the close below handles it.
            logger.info("Quiz %s opened past its closing time; closing immediately.", quiz.id)
        else:
            logger.info("Opened quiz %s (%s)", quiz.id, quiz.type)
            result.opened.append(quiz)

    for quiz in await quiz_repository.find_due_to_close(now):
        scores = await close_quiz(quiz)
        result.closed.append((quiz, scores))

    return result


async def close_quiz(quiz, closed_early_by=None):
    """Close one quiz and fold daily scores into the monthly totals.

    Returns its scores, highest first.
    """
    scores = await score_repository.list_for_quiz(quiz.id, highest_first=True)
    await quiz_repository.close(quiz.id, closed_early_by=closed_early_by)

    if quiz.type == "daily":
        await add_scores_to_monthly_totals(scores, utc_now())

    logger.info(
        "Closed quiz %s (%s)%s", quiz.id, quiz.type, " early by admin" if closed_early_by else ""
    )
    return scores


async def close_quiz_by_id(quiz_id, closed_early_by=None):
    """Close a quiz an admin picked. Returns (quiz, scores) or None if it's already closed."""
    quiz = await quiz_repository.get(quiz_id)
    if not quiz or quiz.isClosed:
        return None
    scores = await close_quiz(quiz, closed_early_by=closed_early_by)
    return quiz, scores


async def add_scores_to_monthly_totals(scores, now):
    month_year = now.strftime("%Y-%m")
    for entry in scores:
        await score_repository.add_to_cumulative(
            entry.userId, month_year, entry.score, entry.timeTakenSeconds
        )
        logger.info("Updated cumulative score for %s", entry.user.firstName)


# --- Listing for admins ------------------------------------------------------
async def list_scheduled():
    return await quiz_repository.find_scheduled()


async def list_open():
    return await quiz_repository.find_open()


async def list_recently_closed(limit=5):
    return await quiz_repository.find_recently_closed(limit=limit)


async def count_questions(quiz_id) -> int:
    return await quiz_repository.count_questions(quiz_id)


# --- Taking a quiz -----------------------------------------------------------
async def find_open_quiz():
    return await quiz_repository.find_open_with_questions()


async def get_existing_score(user_id, quiz_id):
    return await score_repository.get_user_score(user_id, quiz_id)


def pick_questions_for_user(questions):
    """Random subset of the quiz's question pool for one user."""
    per_user = settings_service.get("questions_per_user")
    return random.sample(questions, min(len(questions), per_user))


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
            if (utc_now() - quiz.createdAt).days >= LEADERBOARD_VISIBLE_DAYS:
                return None
            title_suffix = "(Final)"

    scores = await score_repository.list_for_quiz(quiz.id)
    top = _rank(scores, "score")[: settings_service.get("leaderboard_size")]
    if not top:
        return None
    return title_suffix, top


async def get_monthly_leaderboard(month_year):
    entries = await score_repository.list_cumulative_for_month(month_year)
    # A 0 total time is treated like "no time" for tie-breaks.
    ranked = sorted(
        entries,
        key=lambda e: (-e.cumulativeScore, e.timeTakenSeconds if e.timeTakenSeconds else NO_TIME_RECORDED),
    )
    return ranked[:MONTHLY_LEADERBOARD_SIZE]
