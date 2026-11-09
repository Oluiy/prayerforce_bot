"""Keep the deployed web service awake.

Render's free web services sleep after a period without inbound traffic. A
request to our own public URL leaves the service, goes through Render's router
and comes back, which counts as inbound traffic, so the idle timer never fires
while this loop is running.

It cannot wake an instance that has already slept, which is why it starts on
boot and repeats. It does nothing at all when there is no public URL, so local
polling never pings anything.
"""
import logging

import httpx

from config import settings

logger = logging.getLogger(__name__)

PING_INTERVAL_SECONDS = 5 * 60
PING_FIRST_SECONDS = 30
PING_TIMEOUT_SECONDS = 20


async def self_ping(context):
    """Hit our own /health endpoint. A failure is logged and retried next tick."""
    public_url = settings.public_url
    if not public_url:
        return

    url = f"{public_url.rstrip('/')}/health"
    try:
        async with httpx.AsyncClient(timeout=PING_TIMEOUT_SECONDS) as client:
            response = await client.get(url)
        logger.debug("Self-ping %s -> %s", url, response.status_code)
    except Exception as e:
        # Never take the bot down over a keepalive.
        logger.warning("Self-ping failed: %s", e)
