from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from database.prisma_connect import db
import random

QUIZ_QUESTION = 1

async def start_quiz_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check for active quiz
    # We find the latest active quiz that is not closed
    quiz = await db.quiz.find_first(
        where={
            "isActive": True,
            "isClosed": False
        },
        include={"questions": {"include": {"options": True}}},
        order={"weekStart": "desc"}
    )
    
    if not quiz:
        await update.message.reply_text("There is no active quiz at the moment. Check back on Sunday!")
        return ConversationHandler.END

    if not quiz.questions:
        await update.message.reply_text("The quiz seems to have no questions. Please contact admin.")
        return ConversationHandler.END

    # Check if user already attempted this specific quiz
    # First, ensure user exists in DB (sync might be needed or handled in start)
    db_user = await db.user.find_unique(where={"chatId": str(user.id)})
    if not db_user:
        # Create user if missing
        db_user = await db.user.create(
            data={
                "chatId": str(user.id),
                "firstName": user.first_name,
                "lastName": user.last_name,
            }
        )

    existing_score = await db.userscore.find_unique(
        where={
            "userId_quizId": {
                "userId": db_user.id,
                "quizId": quiz.id
            }
        }
    )

    if existing_score:
        await update.message.reply_text(f"You have already taken this quiz! You scored {existing_score.score}.")
        return ConversationHandler.END

    # Initialize session
    questions = quiz.questions
    # Shuffle checks handled in display? No, let's shuffle options
    
    context.user_data["quiz_id"] = quiz.id
    context.user_data["questions"] = questions
    context.user_data["current_index"] = 0
    context.user_data["score"] = 0
    context.user_data["user_id"] = str(user.id)
    
    await update.message.reply_text(f"Starting the {quiz.type} quiz! You have {len(questions)} questions. Good luck!")
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
    
    # Inline keyboard for answers
    keyboard = [[InlineKeyboardButton(opt.text, callback_data=f"ans_{opt.id}")] for opt in options]
    
    keyboard_layout = []
    row = []
    for btn in keyboard:
        row.append(btn[0])
        if len(row) == 2:
            keyboard_layout.append(row)
            row = []
    if row:
        keyboard_layout.append(row)
        
    reply_markup = InlineKeyboardMarkup(keyboard_layout)
    base_text = f"Question {index + 1}/{len(questions)}:\n{question.text}"
    text = f"{base_text}\n\n⏱️ You have 15 seconds to answer!"

    # Cancel any existing timer
    if "question_timer" in context.user_data and context.user_data["question_timer"]:
        context.user_data["question_timer"].schedule_removal()
        
    if update and update.callback_query:
        # If continuing from a callback query, we can edit or send new msg
        # Usually better to send a new message so previous question remains visible
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
    else:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup
        )
    
    context.user_data["timer_for_index"] = index
    
    user_id_val = context.user_data.get("user_id")
    if not user_id_val and update and update.effective_user:
        user_id_val = update.effective_user.id
        
    # Schedule repeating countdown job (1 sec interval)
    job = context.job_queue.run_repeating(
        countdown_job, 
        interval=1,
        first=1,
        data={
            "chat_id": chat_id, 
            "message_id": msg.message_id,
            "user_id": user_id_val,
            "base_text": base_text,
            "reply_markup": reply_markup,
            "time_left": 15,
            "index": index
        },
        chat_id=chat_id,
        user_id=int(user_id_val) if user_id_val else None
    )
    context.user_data["question_timer"] = job

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

    # Verify index hasn't changed
    current_index = context.user_data.get("current_index", 0)
    if current_index != data["index"]:
        job.schedule_removal()
        return

    if time_left > 0:
        # Update UI every second
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{data['base_text']}\n\n⏱️ You have {time_left} seconds left!",
                reply_markup=data["reply_markup"]
            )
        except Exception:
            pass # Ignore if same message text or rate limit hits
    else:
        job.schedule_removal()
        context.user_data["question_timer"] = None
        
        # Time complete
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"{data['base_text']}\n\n⏰ Time's up!",
                reply_markup=None
            )
        except Exception:
            pass

        # Move to next question
        context.user_data["current_index"] += 1
        
        new_index = context.user_data["current_index"]
        questions = context.user_data.get("questions", [])
        
        if new_index >= len(questions):
            await finish_quiz(None, context, chat_id=chat_id)
        else:
            await ask_question(None, context, chat_id=chat_id)

async def handle_user_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # Ack the query
    
    user_answer_id = query.data.replace("ans_", "")
    
    # Cancel existing timer
    if "question_timer" in context.user_data and context.user_data["question_timer"]:
        context.user_data["question_timer"].schedule_removal()
        context.user_data["question_timer"] = None

    index = context.user_data.get("current_index", 0)
    questions = context.user_data.get("questions", [])
    
    if index >= len(questions):
        return await finish_quiz(update, context)

    question = questions[index]
    
    # Identify correct option
    correct_option = next((opt for opt in question.options if opt.isCorrect), None)
    
    selected_option = next((opt for opt in question.options if str(opt.id) == user_answer_id), None)
    
    if correct_option and selected_option and str(selected_option.id) == str(correct_option.id):
        context.user_data["score"] += 1
        response_text = f"{question.text}\n\n✅ Correct! ({selected_option.text})"
    else:
        response_text = f"{question.text}\n\n❌ Wrong! The correct answer was: {correct_option.text if correct_option else 'Unknown'}"
        
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
    # For a scheduled job, update is None, we need user's ID to record score
    # We should have stored user_id in context.user_data
    user_id = context.user_data.get("user_id")
    if not user_id and update:
        user_id = str(update.effective_user.id)
    
    # Save score
    if user_id:
        db_user = await db.user.find_unique(where={"chatId": str(user_id)})
        if db_user:
            await db.userscore.create(
                data={
                    "userId": db_user.id,
                    "quizId": quiz_id,
                    "score": score
                }
            )
    
    msg = f"Quiz finished! 🏆\nYour final score: {score}/{len(context.user_data.get('questions', []))}"
    if update and update.callback_query:
        await update.callback_query.edit_message_text(
            text=msg,
            reply_markup=None
        )
    elif update and update.message:
        await update.message.reply_text(
            msg,
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=msg,
            reply_markup=ReplyKeyboardRemove()
        )
        
    # Clear user data gracefully
    if "question_timer" in context.user_data and context.user_data["question_timer"]:
        context.user_data["question_timer"].schedule_removal()
        
    return ConversationHandler.END

async def cancel_quiz_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz cancelled.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def get_leaderboard_content():
    # 1. Try to find the latest CLOSED quiz
    quiz = await db.quiz.find_first(
        where={
            "isClosed": True
        },
        order={"weekStart": "desc"}
    )

    title_suffix = "(Final)"

    if not quiz:
        # 2. Fallback: Check for an ACTIVE quiz instead (for ongoing monitoring/testing)
        quiz = await db.quiz.find_first(
            where={
                "isActive": True
            },
            order={"weekStart": "desc"}
        )
        title_suffix = "(Live)"

    if not quiz:
        return None

    # Fetch top 10 scores
    top_scores = await db.userscore.find_many(
        where={"quizId": quiz.id},
        include={"user": True},
        order={"score": "desc"},
        take=10
    )

    if not top_scores:
        return f"Leaderboard is empty for {quiz.type} quiz."

    leaderboard_msg = f"🏆 *Leaderboard {title_suffix}* 🏆\n\n"
    medals = ["🥇", "🥈", "🥉"]
    for idx, entry in enumerate(top_scores):
        medal = medals[idx] if idx < 3 else f"{idx+1}."
        user_name = entry.user.firstName
        if entry.user.lastName:
            user_name += f" {entry.user.lastName}"
        leaderboard_msg += f"{medal} {user_name}: {entry.score} pts\n"
    
    leaderboard_msg += "\n🎁 The winner gets their gift at the next family meeting!"
    
    return leaderboard_msg

async def view_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Shows a teaser for the leaderboard with a button to view details.
    """
    content = await get_leaderboard_content()
    
    if not content:
        await update.message.reply_text("No quizzes found for the leaderboard.")
        return

    keyboard = [[InlineKeyboardButton("View Leaderboard 📜", callback_data="view_leaderboard")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🏆 *Leaderboard Update!* 🏆\n\nTap the button below to see who's leading the charts! 👇",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def leaderboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.data == "view_leaderboard":
        content = await get_leaderboard_content()
        if content:
             # Show a pop-up alert with the top 3 (to keep it short enough for alert)
            lines = content.split('\n')
            
            popup_text = "🎉 Current Standings! 🎉\n\n"
            count = 0
            for line in lines:
                if "pts" in line:
                    if count < 3:
                        popup_text += line + "\n"
                        count += 1
            
            if count == 0:
                 popup_text += "No scores yet!"

            # Show the alert (pop-up)
            try:
                await query.answer(text=popup_text, show_alert=True)
            except Exception as e:
                print(f"Error showing alert: {e}")
                await query.answer() # Fallback

            # Update the original message with the full list
            await query.edit_message_text(text=content, parse_mode="Markdown")
        else:
             await query.answer(text="Leaderboard unavailable", show_alert=True)
    else:
        await query.answer()


quiz_user_handler = ConversationHandler(
    entry_points=[CommandHandler("take_quiz", start_quiz_user)],
    states={
        QUIZ_QUESTION: [CallbackQueryHandler(handle_user_answer, pattern="^ans_")]
    },
    fallbacks=[CommandHandler("cancel", cancel_quiz_user)]
)

leaderboard_handler = CommandHandler("leaderboard", view_leaderboard)
leaderboard_callback_handler = CallbackQueryHandler(leaderboard_callback, pattern="^view_leaderboard$")
