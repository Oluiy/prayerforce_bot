"""Database access for quiz scores and monthly cumulative scores."""
import datetime

from database.prisma_connect import db


async def get_user_score(user_id, quiz_id):
    return await db.userscore.find_unique(
        where={"userId_quizId": {"userId": user_id, "quizId": quiz_id}}
    )


async def create_user_score(user_id, quiz_id, score, time_taken_seconds):
    return await db.userscore.create(
        data={
            "userId": user_id,
            "quizId": quiz_id,
            "score": score,
            "timeTakenSeconds": time_taken_seconds,
        }
    )


async def list_for_quiz(quiz_id, highest_first=False):
    kwargs = {"order": {"score": "desc"}} if highest_first else {}
    return await db.userscore.find_many(
        where={"quizId": quiz_id}, include={"user": True}, **kwargs
    )


async def add_to_cumulative(user_id, month_year, score, time_taken_seconds):
    """Add one quiz result to a user's running total for the month."""
    cumulative = await db.dailyquizcumulative.find_unique(
        where={"userId_monthYear": {"userId": user_id, "monthYear": month_year}}
    )
    if cumulative:
        return await db.dailyquizcumulative.update(
            where={"id": cumulative.id},
            data={
                "cumulativeScore": cumulative.cumulativeScore + score,
                "timeTakenSeconds": cumulative.timeTakenSeconds + time_taken_seconds,
                "totalQuizzesCompleted": cumulative.totalQuizzesCompleted + 1,
                "lastUpdated": datetime.datetime.now(datetime.timezone.utc),
            },
        )
    return await db.dailyquizcumulative.create(
        data={
            "userId": user_id,
            "monthYear": month_year,
            "cumulativeScore": score,
            "timeTakenSeconds": time_taken_seconds,
            "totalQuizzesCompleted": 1,
        }
    )


async def list_cumulative_for_month(month_year):
    return await db.dailyquizcumulative.find_many(
        where={"monthYear": month_year}, include={"user": True}
    )
