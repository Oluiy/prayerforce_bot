"""Webhook entry point for deployment.

Run with:
    uvicorn web:app --host 0.0.0.0 --port $PORT --workers 1

One worker only: quiz sessions, admin grants and the settings cache live in
memory, so a second process would not see them.

Telegram delivers updates to POST /telegram; GET /health is a liveness check
and deliberately does not touch the database.
"""
import hmac
import logging
from contextlib import asynccontextmanager

from bootstrap import build_application, shutdown_application
from config import settings
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from telegram import Update

logger = logging.getLogger(__name__)

SECRET_HEADER = "X-Telegram-Bot-Api-Secret-Token"
TELEGRAM_PATH = "/telegram"


@asynccontextmanager
async def lifespan(app: Starlette):
    application = await build_application(polling=False)
    app.state.telegram = application

    await application.start()
    await register_webhook(application)

    try:
        yield
    finally:
        # The webhook is deliberately left registered. Deleting it would make
        # Telegram drop anything sent while the service sleeps or redeploys;
        # left in place, Telegram retries until we are back.
        await shutdown_application(application)


async def register_webhook(application):
    """Point Telegram at this instance. Idempotent, so it runs on every boot."""
    if not settings.public_url:
        raise RuntimeError(
            "RENDER_EXTERNAL_URL is not set, so Telegram has no address to post to."
        )
    if not settings.webhook_secret:
        raise RuntimeError("WEBHOOK_SECRET is not set; refusing to expose the bot.")

    url = f"{settings.public_url.rstrip('/')}{TELEGRAM_PATH}"
    await application.bot.set_webhook(url=url, secret_token=settings.webhook_secret)
    logger.info("Webhook set to %s", url)


async def health(request: Request) -> JSONResponse:
    """Liveness only, so a cold database can never cause a restart loop."""
    return JSONResponse({"status": "ok"})


async def telegram(request: Request) -> Response:
    application = request.app.state.telegram

    # Without this check anyone could post a hand-crafted update pretending to
    # be an admin, so a missing or wrong secret is a hard reject.
    expected = settings.webhook_secret or ""
    supplied = request.headers.get(SECRET_HEADER, "")
    if not expected or not hmac.compare_digest(supplied, expected):
        logger.warning("Rejected a webhook call with a bad secret.")
        return Response(status_code=403)

    try:
        payload = await request.json()
    except Exception:
        return Response(status_code=400)

    try:
        update = Update.de_json(payload, application.bot)
    except Exception:
        logger.exception("Could not parse a Telegram update")
        return Response(status_code=400)

    if update is None:
        return Response(status_code=400)

    # Answer as soon as it is queued. Returning a non-2xx would make Telegram
    # retry, which would run the same command twice.
    await application.update_queue.put(update)
    return Response(status_code=200)


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route(TELEGRAM_PATH, telegram, methods=["POST"]),
    ],
    lifespan=lifespan,
)
