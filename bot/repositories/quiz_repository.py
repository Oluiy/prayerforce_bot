"""Database access for quizzes, questions and options."""
from database.prisma_connect import db

WITH_QUESTIONS = {"questions": {"include": {"options": True}}}


async def get(quiz_id):
    return await db.quiz.find_unique(where={"id": quiz_id})


async def create(quiz_type, week_start, is_active):
    return await db.quiz.create(
        data={
            "weekStart": week_start,
            "isActive": is_active,
            "isClosed": False,
            "type": quiz_type,
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


async def find_active(quiz_type, order_by):
    return await db.quiz.find_first(
        where={"isActive": True, "type": quiz_type},
        order={order_by: "desc"},
    )


async def find_pending(quiz_type, order_by):
    """Latest quiz of this type that hasn't been opened or closed yet."""
    return await db.quiz.find_first(
        where={"isActive": False, "isClosed": False, "type": quiz_type},
        order={order_by: "desc"},
    )


async def find_open_with_questions():
    return await db.quiz.find_first(
        where={"isActive": True, "isClosed": False},
        include=WITH_QUESTIONS,
        order={"weekStart": "desc"},
    )


async def find_latest_started():
    """Newest quiz that is active or already closed."""
    return await db.quiz.find_first(
        where={"OR": [{"isActive": True}, {"isClosed": True}]},
        order={"weekStart": "desc"},
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


async def close(quiz_id):
    return await db.quiz.update(where={"id": quiz_id}, data={"isActive": False, "isClosed": True})


async def close_all_active(quiz_type):
    await db.quiz.update_many(
        where={"type": quiz_type, "isActive": True},
        data={"isActive": False, "isClosed": True},
    )
