"""Database access for quizzes, questions and options."""
from database.prisma_connect import db

WITH_QUESTIONS = {"questions": {"include": {"options": True}}}


async def get(quiz_id):
    return await db.quiz.find_unique(where={"id": quiz_id})


async def create(quiz_type, week_start, is_active=False, opens_at=None, closes_at=None):
    return await db.quiz.create(
        data={
            "weekStart": week_start,
            "isActive": is_active,
            "isClosed": False,
            "type": quiz_type,
            "opensAt": opens_at,
            "closesAt": closes_at,
        }
    )


async def delete(quiz_id):
    await db.quiz.delete(where={"id": quiz_id})


async def add_question(quiz_id, text, options):
    """Create a question with its options. `options` is a list of (text, is_correct)."""
    question = await db.question.create(data={"text": text, "quizId": quiz_id})
    for option_text, is_correct in options:
        await db.option.create(
            data={"text": option_text, "isCorrect": is_correct, "questionId": question.id}
        )
    return question


async def find_active(quiz_type, order_by="createdAt"):
    return await db.quiz.find_first(
        where={"isActive": True, "type": quiz_type},
        order={order_by: "desc"},
    )


async def find_open_with_questions():
    return await db.quiz.find_first(
        where={"isActive": True, "isClosed": False},
        include=WITH_QUESTIONS,
        order={"closesAt": "asc"},
    )


async def find_latest_started():
    """Newest quiz that is active or already closed."""
    return await db.quiz.find_first(
        where={"OR": [{"isActive": True}, {"isClosed": True}]},
        order={"createdAt": "desc"},
    )


async def find_since_with_questions(quiz_type, since):
    return await db.quiz.find_many(
        where={"type": quiz_type, "weekStart": {"gte": since}},
        include=WITH_QUESTIONS,
    )


async def activate(quiz_id):
    return await db.quiz.update(where={"id": quiz_id}, data={"isActive": True})


async def deactivate(quiz_id):
    return await db.quiz.update(where={"id": quiz_id}, data={"isActive": False})


async def close(quiz_id, closed_early_by=None):
    data = {"isActive": False, "isClosed": True}
    if closed_early_by:
        data["closedEarlyBy"] = str(closed_early_by)
    return await db.quiz.update(where={"id": quiz_id}, data=data)


async def close_all_active(quiz_type):
    await db.quiz.update_many(
        where={"type": quiz_type, "isActive": True},
        data={"isActive": False, "isClosed": True},
    )

async def set_schedule(quiz_id, opens_at, closes_at):
    return await db.quiz.update(
        where={"id": quiz_id}, data={"opensAt": opens_at, "closesAt": closes_at}
    )


async def set_type(quiz_id, quiz_type):
    return await db.quiz.update(where={"id": quiz_id}, data={"type": quiz_type})


async def count_questions(quiz_id) -> int:
    return await db.question.count(where={"quizId": quiz_id})


async def find_due_to_open(now):
    """Quizzes whose opening time has arrived but which aren't open yet."""
    return await db.quiz.find_many(
        where={"isActive": False, "isClosed": False, "opensAt": {"lte": now}},
        order={"opensAt": "asc"},
    )


async def find_due_to_close(now):
    """Open quizzes whose closing time has passed."""
    return await db.quiz.find_many(
        where={"isActive": True, "isClosed": False, "closesAt": {"lte": now}},
        order={"closesAt": "asc"},
    )


async def find_scheduled():
    """Quizzes waiting to open."""
    return await db.quiz.find_many(
        where={"isActive": False, "isClosed": False}, order={"opensAt": "asc"}
    )


async def find_open():
    """Quizzes members can take right now."""
    return await db.quiz.find_many(
        where={"isActive": True, "isClosed": False}, order={"closesAt": "asc"}
    )


async def find_recently_closed(limit=5):
    return await db.quiz.find_many(
        where={"isClosed": True}, order={"createdAt": "desc"}, take=limit
    )
