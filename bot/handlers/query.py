from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from random import choice, shuffle
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
)
from handlers.commandHandler import cancel
from Prisma.prisma_connect import db

ASKING = 1  # answer to the question


questions_with_options = [
    {
        "text": "What year was prayer force established?",
        "options": [
            {"text": "2003"},
            {"text": "2002", "isCorrect": True},
            {"text": "2001"},
            {"text": "2005"},
        ],
    },
    {
        "text": 'What was the name of "PrayerForce" when it was established?',
        "options": [
            {"text": "Dunamis", "isCorrect": True},
            {"text": "Illuminos"},
            {"text": "Prayer Unit"},
            {"text": "Prayer Warriors"},
        ],
    },
]

# async def create_questions():
#     try:
#         print("Creating questions...")
#         for q in questions_with_options:
#             question2 = await db.question.create(
#                 data={"text": q["text"], "options": {"create": q["options"]}}
#             )
#             print(f"✅ Created question: {question2.text}")
#     except Exception as e:
#         print(f"❌ Failed to create questions: {e}")


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    questions = await db.question.find_many(include={"options": True})

    if not questions:
        await update.message.reply_text("No available question at the moment!")
        return ConversationHandler.END

    random_question = choice(questions)
    options = random_question.options
    shuffle(options)

    keyboard = []
    for i in range(0, len(options), 2):
        row = []
        for opt in options[i : i + 2]:
            row.append(InlineKeyboardButton(text=opt.text, callback_data=str(opt.id)))
        keyboard.append(row)

    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=random_question.text,
        reply_markup=reply_markup,
    )
    return ASKING


async def get_correct_option_text(question_id: int) -> str:
    correct_option = await db.option.find_first(
        where={"questionId": question_id, "isCorrect": True}
    )
    return correct_option.text if correct_option else "Unknown"


async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Important to answer the callback query

    option_id = query.data  # This is the ID we set earlier
    option = await db.option.find_unique(
        where={"id": int(option_id)}, include={"question": True}
    )

    if option.isCorrect:
        await query.edit_message_text("✅ Correct! You're a genius! 🚀")
    else:
        await query.edit_message_text(
            f"❌ Nope. The correct answer to *{option.question.text}* is: *{await get_correct_option_text(option.questionId)}*",
            parse_mode="Markdown",
        )
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("question", ask_question)],
    states={
        ASKING: [CallbackQueryHandler(handle_answer)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)
