import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables immediately
load_dotenv()

import pytz
from datetime import time

# all modules(as handlers)
# In your main.py
from handlers.payment import payment_callback_handler
from handlers.commandHandler import *
from handlers.annoucement import annoucement_handler
from handlers.query import conv_handler, handle_answer
from handlers.counsel import conv as counsel_conv
from handlers.quiz_admin import quiz_admin_handler
from handlers.quiz_user import quiz_user_handler, leaderboard_handler, leaderboard_callback_handler
from handlers.quiz_jobs import open_weekly_quiz, close_weekly_quiz
from database.prisma_connect import db
from handlers.broadcastmessage import *
from handlers.payment import *

# basic config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

load_dotenv()
bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN")


# the "/start" command to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_exist = await db.user.find_unique(where={"chatId": str(user.id)})

    # If user doesn't exist, create a new one
    if not user_exist:
        userInfo = await db.user.create(
            data={
                "chatId": str(user.id),
                "firstName": user.first_name,
                "lastName": user.last_name,
            }
        )
    else:
        userInfo = user_exist

    print(
        f"User Info → ID: {user.id}, Username: @{user.username}, Full Name: {user.full_name}"
    )

    user_firstname = update.effective_user.first_name
    # userio = update.effective_user.full_name
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Hi {user_firstname}! I'm Tefillah, the Prayer Force bot\n\n"
        "I’m here to help you stay connected with the Prayer Force family. Through me, you can get helpful information, learn new things, and even have a little fun along the way.\n\n"
        "You can also share your testimonies, because every testimony reminds us of what God is doing among us. If you need prayers, you can send in a prayer request anonymously, and the family will stand with you in prayer.\n\n"
        "Take a moment to explore. There’s something here for you.\n\n"
        "Remember Prayer Force loves you but Jesus loves you more!!!\n"
        "Don't forget to visit the office today🌚.\n\n"
        "Welcome again❤️",
        parse_mode="Markdown",
    )
    return userInfo


# ensuring the main application is running which power every other functionality of the bot
async def main():
    print("Starting bot...")
    try:
        print("Connecting to database...")
        await db.connect()
        print("Database connected successfully!")
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN is not set.")
        return

    print("Building application...")
    application = ApplicationBuilder().token(bot_token).post_init(commands).build()

    # application handlers
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    application.add_handler(conv_handler)
    application.add_handler(command_handler)
    application.add_handler(history_handler)
    application.add_handler(sunday_meetings_handler)
    application.add_handler(purchase_shirt_handler)
    application.add_handler(payment_callback_handler)
    application.add_handler(CallbackQueryHandler(handle_answer, pattern=r"^\d+$"))
    application.add_handler(annoucement_handler)
    # application.add_handler(CallbackQueryHandler(handle_answer)) # Removed duplicate
    application.add_handler(payment_conv_handler)
    application.add_handler(CommandHandler("universe", send_payment_button))
    application.add_handler(payment_button_handler)
    application.add_handler(quiz_admin_handler)
    application.add_handler(quiz_user_handler)
    application.add_handler(leaderboard_handler)
    application.add_handler(leaderboard_callback_handler)
    # application.add_handler(open_weekly_quiz)
    # application.add_handler(close_weekly_quiz)
    application.add_handler(counsel_conv)
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"start"), start)
    )

    # await create_questions()
    # await sync_users()
    # await check_birthdays()

    job_queue = application.job_queue
    lagos_tz = pytz.timezone("Africa/Lagos")

    reminder_time = time(hour=15, minute=6, second=30, tzinfo=lagos_tz)
    reminder_time2 = time(hour=15, minute=6, second=0, tzinfo=lagos_tz)

    # job_queues
    job_queue.run_daily(Broadcast, time=reminder_time2)
    job_queue.run_daily(startup_broadcast, time=reminder_time, days=(2, 4))
    job_queue.run_daily(daily_recharge, time=reminder_time, days=(0, 1, 3, 6))

    # Weekly Quiz Scheduler
    job_queue.run_daily(open_weekly_quiz, time=time(hour=12, minute=0, second=0, tzinfo=lagos_tz), days=(6,))  # Opens Sunday 12 PM
    job_queue.run_daily(close_weekly_quiz, time=time(hour=12, minute=0, second=0, tzinfo=lagos_tz), days=(4,))  # Closes Friday 12 PM

    print("Initializing application...")
    await application.initialize()
    await application.start()
    print("Starting polling...")
    await application.updater.start_polling()
    print("Bot is up and running! 🚀")

    try:
        # Keep the application running
        stop_signal = asyncio.Event()
        await stop_signal.wait()
    finally:
        # Ensure we disconnect the database when stopping
        print("Stopping bot...")
        await db.disconnect()
        print("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())

# to activate the virtual environment
# use the command source venv/bin/activate
