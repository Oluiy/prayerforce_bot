from telegram.ext import Application

from handlers.announcement import announcement_handler
from handlers.broadcast import manual_broadcast_handler
from handlers.forms import prayer_request_handler, testimony_handler
from handlers.info import history_handler, purchase_shirt_handler, sunday_meetings_handler
from handlers.leaderboard import leaderboard_callback_handler, leaderboard_handler
from handlers.menu import commands_handler
from handlers.quiz_admin import quiz_admin_handler
from handlers.quiz_user import quiz_user_handler
from handlers.start import start_handler, start_text_handler

# Order matters: Telegram updates go to the first handler that matches.
HANDLERS = [
    start_handler,
    commands_handler,
    history_handler,
    sunday_meetings_handler,
    purchase_shirt_handler,
    announcement_handler,
    manual_broadcast_handler,
    prayer_request_handler,
    testimony_handler,
    quiz_admin_handler,
    quiz_user_handler,
    leaderboard_handler,
    leaderboard_callback_handler,
    start_text_handler,  # catch-all for text containing "start", keep last
]


def register_handlers(app: Application):
    for handler in HANDLERS:
        app.add_handler(handler)
