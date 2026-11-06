import logging

import messages
from config import settings
from services import admin_service
from telegram import BotCommand, BotCommandScopeChat, Update
from telegram.ext import Application, CommandHandler, ContextTypes
from utils.auth import is_admin

logger = logging.getLogger(__name__)


def _commands(pairs):
    return [BotCommand(name, description) for name, description in pairs]


MEMBER_MENU = lambda: _commands(messages.BOT_COMMANDS)
ADMIN_MENU = lambda: _commands(messages.BOT_COMMANDS + messages.ADMIN_COMMANDS)


async def apply_admin_menu(bot, chat_id) -> bool:
    """Show the admin commands in one member's menu. Used when access is granted."""
    try:
        await bot.set_my_commands(ADMIN_MENU(), scope=BotCommandScopeChat(chat_id=chat_id))
        return True
    except Exception:
        logger.warning("Could not set the admin menu for %s", chat_id)
        return False


async def apply_member_menu(bot, chat_id) -> bool:
    """Put a member's menu back to normal. Used when access ends."""
    try:
        await bot.set_my_commands(MEMBER_MENU(), scope=BotCommandScopeChat(chat_id=chat_id))
        return True
    except Exception:
        logger.warning("Could not reset the menu for %s", chat_id)
        return False


async def set_bot_commands(app: Application):
    """Register the command menus. Runs once at startup.

    Everyone sees the member commands; admins also see the admin ones.
    """
    await app.bot.set_my_commands(_commands(messages.BOT_COMMANDS))

    # Permanent admins, plus anyone whose temporary access is still running.
    for admin_id in list(settings.admin_ids) + admin_service.temporary_ids():
        # An admin who has never messaged the bot can't have a scoped menu yet.
        await apply_admin_menu(app.bot, admin_id)


async def refresh_commands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Re-apply the menus, e.g. after an admin messages the bot for the first time."""
    if not is_admin(update.effective_user):
        await update.message.reply_text(messages.NOT_AUTHORIZED)
        return
    await set_bot_commands(context.application)
    await update.message.reply_text(messages.COMMAND_MENU_REFRESHED)


commands_handler = CommandHandler("commands", refresh_commands)
