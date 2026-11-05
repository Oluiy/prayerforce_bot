"""Fixed application settings that don't come from the environment."""
from datetime import time

import pytz

# --- General -----------------------------------------------------------------
TIMEZONE = pytz.timezone("Africa/Lagos")

# --- External links ----------------------------------------------------------
PRAYER_REQUEST_URL = "https://bit.ly/LetUsPrayWithYou"
TESTIMONY_FORM_URL = "https://forms.gle/btif8k48fPW9Lh6g7"

# --- Google Sheets -----------------------------------------------------------
GOOGLE_CREDENTIALS_FILE = "credentials.json"
GOOGLE_SHEETS_SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# --- AI quiz generation ------------------------------------------------------
GEMINI_MODEL = "gemini-2.5-flash-lite"
MAX_NOTES_CHARS = 50_000
MIN_GENERATED_QUESTIONS = 20
MAX_GENERATED_QUESTIONS = 40
WORDS_PER_GENERATED_QUESTION = 80

# --- Quiz rules --------------------------------------------------------------
QUESTIONS_PER_USER = 12            # random questions each user gets from the pool
QUESTION_TIME_LIMIT_SECONDS = 15
MONTHLY_RECAP_QUESTIONS = 40
MONTHLY_RECAP_LOOKBACK_DAYS = 30
LEADERBOARD_SIZE = 10
MONTHLY_LEADERBOARD_SIZE = 15
LEADERBOARD_VISIBLE_DAYS = 7       # closed quizzes stay on /leaderboard this long

# --- Quiz scheduling ---------------------------------------------------------
# Each quiz carries its own opensAt/closesAt, chosen by the admin who creates
# it. These two are only the defaults offered as buttons in that menu.
DEFAULT_QUIZ_OPEN_TIME = time(hour=8, minute=0)
DEFAULT_QUIZ_CLOSE_TIME = time(hour=23, minute=0)

# How often the sweep checks for quizzes due to open or close.
SCHEDULE_SWEEP_SECONDS = 60

# --- Recurring job times (all times in TIMEZONE) -----------------------------
# These jobs aren't tied to one quiz, so they stay on a fixed daily schedule.
MONTHLY_LEADERBOARD_TIME = time(hour=23, minute=30, tzinfo=TIMEZONE)
MONTHLY_RECAP_TIME = time(hour=12, minute=0, tzinfo=TIMEZONE)
BIRTHDAY_MESSAGE_TIME = time(hour=8, minute=0, tzinfo=TIMEZONE)
