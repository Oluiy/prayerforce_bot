from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, ContextTypes

import messages


async def set_bot_commands(app: Application):
    """Register the command menu shown in Telegram. Runs once at startup."""
    await app.bot.set_my_commands([BotCommand(name, desc) for name, desc in messages.BOT_COMMANDS])


async def refresh_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.set_my_commands([BotCommand(name, desc) for name, desc in messages.BOT_COMMANDS])
    await update.message.reply_text(messages.COMMAND_MENU_REFRESHED)


commands_handler = CommandHandler("commands", refresh_commands)
