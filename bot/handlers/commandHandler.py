from telegram.ext import Application, ConversationHandler, ContextTypes, CommandHandler
from telegram import BotCommand, Update


async def commandss(app: Application):
    commands = [
        BotCommand("start", "Get to know Tefillah"),
        BotCommand("announcement", "To get all necessary annoucement"),
        BotCommand("question", "Random questions from the database"),
        BotCommand("history", "Want to know the history of Prayer Force?🙂 you can \'use the command\'"),
        BotCommand('Sunday-meetings','Pre-service and Post-service'),
    ]

    await app.bot.set_my_commands(commands)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Quiz cancelled."
    )
    return ConversationHandler.END


command_handler = CommandHandler("commands", commandss)
