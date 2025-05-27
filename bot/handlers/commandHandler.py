# from telegram.ext import Application, ConversationHandler, ContextTypes, CommandHandler
# from telegram import BotCommand, Update


# async def commands(app: Application):
#     commands_list = [
#         BotCommand("start", "Get to know Tefillah"),
#         BotCommand("announcement", "To get all necessary annoucement"),
#         BotCommand("question", "Random questions from the database"),
#         BotCommand("history", "Want to know the history of Prayer Force?🙂 you can \'use the command\'"),
#         BotCommand("Sunday-meetings","Pre-service and Post-service"),
#         BotCommand("Purchase_shirt", "Want to purchase shirt or food or both?"),
#         BotCommand("donate", "Make a donation to Prayer Force"),
#         BotCommand("donate_button", "Show donation button")
#     ]

#     await app.bot.set_my_commands(commands_list)


# async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await context.bot.send_message(
#         chat_id=update.effective_chat.id, text="Quiz cancelled."
#     )
#     return ConversationHandler.END


# command_handler = CommandHandler("commands", commands)

from telegram.ext import Application, ConversationHandler, ContextTypes, CommandHandler
from telegram import BotCommand, Update


async def commands(app: Application):
    # Register commands in the bot's command menu
    commands_list = [
        BotCommand("start", "Get to know Tefillah"),
        BotCommand("announcement", "To get all necessary annoucement"),
        BotCommand("question", "Random questions from the database"),
        BotCommand("history", "Want to know the history of Prayer Force?🙂 you can 'use the command'"),
        BotCommand("Sunday_meetings", "Pre-service and Post-service"),
        BotCommand("Purchase_shirt", "Want to purchase shirt or food or both?"),
        BotCommand("donate", "Make a donation to Prayer Force"),
        BotCommand("donate_button", "Show donation button")
    ]

    await app.bot.set_my_comands(commands_list)


# Command handler functions for each command
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Prayer Force was founded in 2020 as a spiritual movement dedicated to prayer and intercession. "
        "Since then, we've grown into a community of believers committed to seeking God's presence through prayer."
    )

async def sunday_meetings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Our Sunday meetings schedule:\n\n"
        "Pre-service Prayer: 8:00 AM - 9:00 AM\n"
        "Main Service: 9:30 AM - 11:30 AM\n"
        "Post-service Prayer: 12:00 PM - 1:00 PM"
    )

async def purchase_shirt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "To purchase Prayer Force merchandise:\n\n"
        "1. Prayer Force T-shirt - ₦5,000\n"
        "2. Prayer Journal - ₦3,500\n\n"
        "Please use the /donate command to make payment and specify what you're purchasing in the description."
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Operation cancelled."
    )
    return ConversationHandler.END


# Create command handlers
command_handler = CommandHandler("commands", commands)
history_handler = CommandHandler("history", history_command)
sunday_meetings_handler = CommandHandler("meetings", sunday_meetings_command)
purchase_shirt_handler = CommandHandler("merch", purchase_shirt_command)