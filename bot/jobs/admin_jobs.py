"""Ending temporary admin access when its time runs out."""
import logging

import messages
from handlers.menu import apply_member_menu
from services import admin_service
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def expire_admin_grants(context: ContextTypes.DEFAULT_TYPE):
    """Put expired admins back to a normal member menu and tell them.

    Access itself already stops the moment it expires — this is the tidy-up.
    """
    for telegram_id in admin_service.expire_due():
        await apply_member_menu(context.bot, telegram_id)
        try:
            await context.bot.send_message(
                chat_id=telegram_id, text=messages.ADMIN_EXPIRED_NOTICE
            )
        except Exception:
            logger.warning("Could not tell %s their admin access expired", telegram_id)
