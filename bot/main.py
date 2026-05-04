import logging
import sys
print(f"Script starting... Python version: {sys.version}")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
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
from handlers.commandHandler import *
from handlers.annoucement import annoucement_handler
from handlers.form_helper import pr_request, testimony_request
from handlers.quiz_admin import quiz_admin_handler
from handlers.quiz_user import quiz_user_handler, leaderboard_handler, leaderboard_callback_handler
from handlers.quiz_jobs import open_weekly_quiz, close_weekly_quiz, generate_monthly_recap, open_daily_quiz, close_daily_quiz, send_monthly_cumulative_leaderboard
from database.prisma_connect import db
from handlers.broadcastmessage import *
# from handlers.payment import *

# basic config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO, force=True
)

# Avoid logging raw Telegram request URLs that include the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("telegram.request").setLevel(logging.WARNING)

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
    application.add_handler(command_handler)
    application.add_handler(history_handler)
    application.add_handler(sunday_meetings_handler)
    application.add_handler(purchase_shirt_handler)
    application.add_handler(annoucement_handler)
    application.add_handler(manual_broadcast_handler)
    application.add_handler(pr_request)
    application.add_handler(testimony_request)
    application.add_handler(quiz_admin_handler)
    application.add_handler(quiz_user_handler)
    application.add_handler(leaderboard_handler)
    application.add_handler(leaderboard_callback_handler)
    application.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"start"), start)
    )

    # await create_questions()
    # await sync_users()
    # await check_birthdays()

    job_queue = application.job_queue
    lagos_tz = pytz.timezone("Africa/Lagos")

    # reminder_time = time(hour=15, minute=6, second=30, tzinfo=lagos_tz)
    # reminder_time2 = time(hour=15, minute=6, second=0, tzinfo=lagos_tz)

    # job_queues
    # job_queue.run_daily(Broadcast, time=reminder_time2)
    # job_queue.run_daily(startup_broadcast, time=reminder_time, days=(2, 4))
    # job_queue.run_daily(daily_recharge, time=reminder_time, days=(0, 1, 3, 6))

    # Weekly Quiz Scheduler
    job_queue.run_daily(open_weekly_quiz, time=time(hour=12, minute=0, second=0, tzinfo=lagos_tz), days=(6,))  # Opens Sunday 12 PM
    job_queue.run_daily(close_weekly_quiz, time=time(hour=19, minute=0, second=0, tzinfo=lagos_tz), days=(5,))  # Closes Friday 6 PM

    # Daily Quiz Scheduler
    job_queue.run_daily(open_daily_quiz, time=time(hour=8, minute=0, second=0, tzinfo=lagos_tz))  # Opens every day at 8 AM
    job_queue.run_daily(close_daily_quiz, time=time(hour=23, minute=0, second=0, tzinfo=lagos_tz))  # Closes every day at 11 PM
    
    # Monthly Cumulative Leaderboard (Runs daily at 11:30 PM, only sends on last day of month)
    job_queue.run_daily(send_monthly_cumulative_leaderboard, time=time(hour=23, minute=30, second=0, tzinfo=lagos_tz))

    # Monthly Recap Scheduler (Runs daily, but the job itself checks if it's the last day of the month)
    job_queue.run_daily(generate_monthly_recap, time=time(hour=12, minute=0, second=0, tzinfo=lagos_tz))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    print("Bot is up and running! 🚀")

    try:
        stop_signal = asyncio.Event()
        await stop_signal.wait()
    finally:
        await db.disconnect()
        print("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())

# to activate the virtual environment
# use the command source venv/bin/activate
