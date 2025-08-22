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
import pytz
from datetime import time

# all modules(as handlers)
# In your main.py
from handlers.payment import payment_callback_handler
from handlers.commandHandler import *
from handlers.annoucement import annoucement_handler
from handlers.query import *
from Prisma.prisma_connect import db
from handlers.broadcastmessage import *
from handlers.payment import *

# basic config
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

#Using environment variables
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
        text=f"Hi <b>{user_firstname}!</b> I'm Tefillah, the Prayer Force bot\n"
        "Sending you some love❤️.\n\n"
        "Remember Prayer Force loves you but Jesus loves you more!!!\n"
        "Don't forget to visit the office today🌚.\n",
        parse_mode="HTML",
    )
    return userInfo


# ensuring the main application is running which power every other functionality of the bot
async def main():
    await db.connect()
    application = ApplicationBuilder().token(bot_token).build()

    application.post_init = commands
    # application handlers
    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)
    application.add_handler(conv_handler)
    application.add_handler(command_handler)
    application.add_handler(history_handler)  # Add this
    application.add_handler(sunday_meetings_handler)  # Add this
    application.add_handler(purchase_shirt_handler)
    application.add_handler(payment_callback_handler) 
    application.add_handler(annoucement_handler)
    application.add_handler(payment_conv_handler)
    application.add_handler(CommandHandler("universe", send_payment_button))
    application.add_handler(payment_button_handler)
    application.add_handler(CallbackQueryHandler(handle_answer, pattern="^\\d+$"))



    # application.add_handler(CommandHandler("merch", purchase_shirt_command))
    # application.add_handler(checkout_conv_handler)
    # application.add_handler(CallbackQueryHandler(handle_cart_actions, 
    #                 pattern="^(add_to_cart:|view_cart|checkout|back_to_menu|quantity_|add_item_to_cart|clear_cart)$"))
    # application.add_handler(CallbackQueryHandler(handle_payment_verification, pattern="^verify_payment:"))

    await create_questions()
    # await sync_users()
    # await check_birthdays()

    job_queue = application.job_queue
    lagos_tz = pytz.timezone('Africa/Lagos')

    reminder_time = time(hour=22, minute=28, second=50, tzinfo=lagos_tz)  
    reminder_time2 = time(hour=22, minute=28, second=50, tzinfo=lagos_tz)  

    #job_queues
    job_queue.run_daily(Broadcast, time=reminder_time2)
    job_queue.run_daily(startup_broadcast, time=reminder_time, days=(2, 4))
    job_queue.run_daily(daily_recharge, time=reminder_time, days=(0, 1, 3, 6))

    

    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    try:
        # Keep the application running
        stop_signal = asyncio.Event()
        await stop_signal.wait()
    finally:
        # Ensure we disconnect the database when stopping
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

# to activate the virtual environment
# use the command source venv/bin/activate
