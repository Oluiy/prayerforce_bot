"""Send messages to every member of the current session."""
import logging

from services import session_service

logger = logging.getLogger(__name__)


async def broadcast_text(bot, text, **send_kwargs):
    """Send `text` to all members. Returns (sent_count, failed_count)."""
    return await _broadcast(
        lambda user: bot.send_message(chat_id=user.chatId, text=text, **send_kwargs)
    )


async def broadcast_copy(bot, from_chat_id, message_id):
    """Copy an existing message (any type) to all members. Returns (sent_count, failed_count)."""
    return await _broadcast(
        lambda user: bot.copy_message(
            chat_id=user.chatId, from_chat_id=from_chat_id, message_id=message_id
        )
    )


async def _broadcast(send):
    sent = failed = 0
    for user in await session_service.members():
        try:
            await send(user)
            sent += 1
        except Exception as e:
            logger.warning("Failed to send broadcast to %s (%s): %s", user.firstName, user.chatId, e)
            failed += 1
    return sent, failed
