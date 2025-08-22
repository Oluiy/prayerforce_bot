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
        "text": "What does the the greek word Katalambano mean",
        "options": [
            {"text": "To seize", "isCorrect": True},
            {"text": "To Generate"},
            {"text": "To Glorify"},
            {"text": "To Edify"},
        ],
    },
    {
        "text": "What day and time does get edified hold?",
        "options": [
            {"text": "Thursday, 5:30pm"},
            {"text": "Friday, 5:35pm"},
            {"text": "Sunday, 2:00pm"},
            {"text": "Friday, 5:30pm", "isCorrect": True},
        ],
    },
    {
        "text": "Which verse in the Bible expounds on focus?",
        "options": [
            {"text": "Matthew 4:11"},
            {"text": "Mark 1:23"},
            {"text": "Luke 2:52"},
            {"text": "Matthew 6:22", "isCorrect": True}
        ]
    },
    {
        "text": "Be not overcome of evil, but overcome evil with good.",
        "options": [
            {"text": "1 Samuel 4:11"},
            {"text": "Romans 12:21", "isCorrect": True},
            {"text": "1 Kings 1:23"},
            {"text": "Hebrews 2:14"}
        ]
    },
    {
        "text": "Brain Teser😉 \nWhich African nation is the largest in land size",
        "options": [
            {"text": "Nigeria"},
            {"text": "South Afirca"},
            {"text": "Algeria", "isCorrect": True},
            {"text": "Egypt"}
        ]
    },
    {
        "text": "Which Bible verses says \"God is Love❤️\"?",
        "options": [
            {"text": "1 John 4:8", "isCorrect": True},
            {"text": "1 John 5:2"},
            {"text": "2 John 1:7"},
            {"text": "John 11:4"}
        ]
    },
    {
        "text": "God has given you🫵 POWER to tread upon serpents and scorpions and you shall not be hurt.",
        "options": [
            {"text": "Luke 10:24"},
            {"text": "Luke 10:21"},
            {"text": "Luke 10:19", "isCorrect": True},
            {"text": "Romans 3:11"}
        ]
    }
]

async def create_questions():
    try:
        print("Creating questions...")
        for q in questions_with_options:
            question2 = await db.question.create(
                data={"text": q["text"], "options": {"create": q["options"]}}
            )
            print(f"✅ Created question: {question2.text}")
    except Exception as e:
        print(f"❌ Failed to create questions: {e}")


async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):

    questions = await db.question.find_many(include={"options": True})

    if not questions:
        await update.message.reply_text("No available question at the moment!")
        return ConversationHandler.END
    
    # Initialize session data if not exists
    if "asked_questions" not in context.user_data:
        context.user_data["asked_questions"] = set()
        context.user_data["correct_count"] = 0
        context.user_data["total_answered"] = 0

    asked_questions = context.user_data.get("asked_questions", set())

    available_questions = [q for q in questions if q.id not in asked_questions]

    if not available_questions:
        total_answered = context.user_data.get("total_answered", 0)
        correct_count = context.user_data.get("correct_count", 0)
        failed_count = total_answered - correct_count
        
        completion_message = (
            f"🎉 Quiz Complete!\n\n"
            f"📊 Final Results:\n"
            f"✅ Correct: {correct_count}\n"
            f"❌ Failed: {failed_count}\n"
            f"📝 Total Answered: {total_answered}\n\n"
            f"Great job completing all questions!"
        )
        
        # Send message using bot context to ensure it works regardless of update type
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=completion_message
        )
        
        # Clear session data
        context.user_data.pop("asked_questions", None)
        context.user_data.pop("correct_count", None)
        context.user_data.pop("total_answered", None)
        return ConversationHandler.END
    

    random_question = choice(available_questions)
    options = random_question.options
    shuffle(options)

    keyboard = []
    for i in range(0, len(options), 2):
        row = []
        for opt in options[i : i + 2]:
            row.append(InlineKeyboardButton(text=opt.text, callback_data=str(opt.id)))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Quit Quiz", callback_data="quit_quiz")])

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data["current_question_id"] = random_question.id
    asked_questions.add(random_question.id)
    context.user_data["asked_questions"] = asked_questions


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
    await query.answer() # Important to answer the callback query

    if query.data == "quit_quiz":
        # Get current stats
        total_answered = context.user_data.get("total_answered", 0)
        correct_count = context.user_data.get("correct_count", 0)
        failed_count = total_answered - correct_count
        
        quiz_summary = (
            f"🏁 Quiz Ended\n\n"
            f"📊 Your Results:\n"
            f"✅ Correct: {correct_count}\n"
            f"❌ Failed: {failed_count}\n"
            f"📝 Total Answered: {total_answered}\n\n"
            f"Thanks for playing! 👋"
        )
        
        await query.edit_message_text(quiz_summary)
        
        # Clear session data
        context.user_data.pop("asked_questions", None)
        context.user_data.pop("current_question_id", None)
        context.user_data.pop("correct_count", None)
        context.user_data.pop("total_answered", None)
        return ConversationHandler.END

    option_id = query.data  # This is the ID we set earlier
    option = await db.option.find_unique(
        where={"id": int(option_id)}, include={"question": True}
    )

    # Update counters
    context.user_data["total_answered"] = context.user_data.get("total_answered", 0) + 1

    if option.isCorrect:
        context.user_data["correct_count"] = context.user_data.get("correct_count", 0) + 1
        await query.edit_message_text("✅ Correct!")
    else:
        await query.edit_message_text(
            f"❌ Nope. The correct answer to *{option.question.text}* is: *{await get_correct_option_text(option.questionId)}*",
            parse_mode="Markdown",
        )
    return await ask_question(update, context)


conv_handler = ConversationHandler(
    entry_points=[CommandHandler("question", ask_question)],
    states={
        ASKING: [CallbackQueryHandler(handle_answer)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)
