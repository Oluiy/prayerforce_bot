"""Telling members things. Used by both the schedule sweep and admin commands."""
import logging

import keyboards
import messages
from services import broadcast_service

logger = logging.getLogger(__name__)


async def announce_quiz_open(bot, quiz):
    logger.info("Announcing open quiz %s", quiz.id)
    return await broadcast_service.broadcast_text(
        bot, messages.quiz_open(quiz.type, quiz.closesAt), parse_mode="Markdown"
    )


async def announce_quiz_closed(bot, quiz, scores):
    """Daily quizzes announce the winner; others link to the full leaderboard."""
    if quiz.type == "daily":
        if not scores:
            logger.info("Quiz %s closed with no participants; nothing to announce.", quiz.id)
            return 0, 0
        winner = scores[0]
        return await broadcast_service.broadcast_text(
            bot,
            messages.daily_winner(winner.user.firstName, winner.score),
            parse_mode="Markdown",
        )

    return await broadcast_service.broadcast_text(
        bot,
        messages.quiz_closed_teaser(quiz.type),
        reply_markup=keyboards.view_results_markup(messages.VIEW_RESULTS_BUTTON, quiz_id=quiz.id),
        parse_mode="Markdown",
    )
