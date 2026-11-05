from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import Application, CommandHandler, ContextTypes

import messages
from config import settings
from utils.auth import is_admin


def _commands(pairs):
    return [BotCommand(name, description) for name, description in pairs]


async def set_bot_commands(app: Application):
    """Register the command menus. Runs once at startup.

    Everyone sees the member commands; admins also see the admin ones.
    """
    await app.bot.set_my_commands(_commands(messages.BOT_COMMANDS))

    admin_menu = _commands(messages.BOT_COMMANDS + messages.ADMIN_COMMANDS)
    for admin_id in settings.admin_ids:
        try:
            await app.bot.set_my_commands(admin_menu, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception:
            # An admin who has never messaged the bot can't have a scoped menu yet.
            pass


async def refresh_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user):
        await update.message.reply_text(messages.NOT_AUTHORIZED)
        return
    await set_bot_commands(context.application)
    await update.message.reply_text(messages.COMMAND_MENU_REFRESHED)


commands_handler = CommandHandler("commands", refresh_commands)
