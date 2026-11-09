"""Admin-editable settings.

Each setting has a default in config/constants.py. The database only holds
values an admin has changed, so a fresh install needs no seeding.

Values are cached in memory and reloaded on change, so reads are cheap.
"""
import logging

from config import constants as c
from repositories import setting_repository
from utils.dates import TimeParseError, format_time_of_day, parse_time_of_day

logger = logging.getLogger(__name__)

TIME = "time"
TEXT = "text"
NUMBER = "number"


class SettingDef:
    """One editable setting: how to show it, and how to check a new value."""

    def __init__(self, key, label, kind, default, hint="", minimum=None, maximum=None):
        self.key = key
        self.label = label
        self.kind = kind
        self.default = default
        self.hint = hint
        self.minimum = minimum
        self.maximum = maximum

    def to_text(self, value) -> str:
        if self.kind == TIME:
            return format_time_of_day(value)
        return str(value)

    def parse(self, raw: str):
        """Turn admin input into a stored value, or raise ValueError with a reason."""
        raw = (raw or "").strip()
        if not raw:
            raise ValueError("That was empty. Please send a value.")

        if self.kind == TIME:
            try:
                return parse_time_of_day(raw)
            except TimeParseError:
                raise ValueError("I couldn't read that as a time. Try something like 8:00 PM or 20:00.")

        if self.kind == NUMBER:
            if not raw.lstrip("-").isdigit():
                raise ValueError("Please send a whole number, e.g. 12.")
            number = int(raw)
            if self.minimum is not None and number < self.minimum:
                raise ValueError(f"Too small. The lowest allowed is {self.minimum}.")
            if self.maximum is not None and number > self.maximum:
                raise ValueError(f"Too big. The highest allowed is {self.maximum}.")
            return number

        if len(raw) > 300:
            raise ValueError("That's too long. Please keep it under 300 characters.")
        return raw

    def serialize(self, value) -> str:
        if self.kind == TIME:
            return value.strftime("%H:%M")
        return str(value)

    def deserialize(self, stored: str):
        if self.kind == TIME:
            return parse_time_of_day(stored)
        if self.kind == NUMBER:
            return int(stored)
        return stored


# Order here is the order shown in /settings.
DEFINITIONS = [
    SettingDef("pre_service_time", "Pre-service prayer", TEXT, c.PRE_SERVICE_TIME,
               "Shown by /meetings, e.g. 7:00 AM - 7:30 AM"),
    SettingDef("post_service_time", "Post-service prayer", TEXT, c.POST_SERVICE_TIME,
               "Shown by /meetings, e.g. 8:20 AM - 8:50 AM"),
    SettingDef("tuesday_meeting_reminder_time", "Tuesday service reminder sent at", TIME, c.TUESDAY_MEETING_REMINDER_TIME,
               "Reminder sent on Monday night",),
    SettingDef("thursday_meeting_reminder_time", "Thursday service reminder sent at", TIME, c.THURSDAY_MEETING_REMINDER_TIME,
               "Reminder sent on Wednesday night",),
    SettingDef("sunday_meeting_reminder_time", "Sunday service reminder sent at", TIME, c.SUNDAY_MEETING_REMINDER_TIME,
               "Reminder sent on Saturday night",),
    SettingDef("announcement_time", "Announcement meeting time", TEXT, c.ANNOUNCEMENT_TIME,
               "Used in /announcement, e.g. 5:30pm"),
    SettingDef("default_quiz_open_time", "Default quiz open time", TIME, c.DEFAULT_QUIZ_OPEN_TIME,
               "Offered as a button when scheduling a new quiz"),
    SettingDef("default_quiz_close_time", "Default quiz close time", TIME, c.DEFAULT_QUIZ_CLOSE_TIME,
               "Offered as a button when scheduling a new quiz"),
    SettingDef("birthday_message_time", "Birthday messages sent at", TIME, c.BIRTHDAY_MESSAGE_TIME),
    SettingDef("monthly_leaderboard_time", "Monthly leaderboard sent at", TIME, c.MONTHLY_LEADERBOARD_TIME),
    SettingDef("monthly_recap_time", "Monthly recap quiz built at", TIME, c.MONTHLY_RECAP_TIME),
    SettingDef("questions_per_user", "Questions each member answers", NUMBER, c.QUESTIONS_PER_USER,
               minimum=1, maximum=50),
    SettingDef("question_seconds", "Seconds allowed per question", NUMBER, c.QUESTION_TIME_LIMIT_SECONDS,
               minimum=5, maximum=300),
    SettingDef("leaderboard_size", "Names shown on the leaderboard", NUMBER, c.LEADERBOARD_SIZE,
               minimum=3, maximum=50),
    SettingDef("tshirt_price", "T-shirt price", TEXT, c.TSHIRT_PRICE, "e.g. ₦5,000"),
    SettingDef("journal_price", "Prayer journal price", TEXT, c.JOURNAL_PRICE, "e.g. ₦3,500"),
]

BY_KEY = {definition.key: definition for definition in DEFINITIONS}

_cache: dict[str, object] | None = None


def definition(key: str) -> SettingDef:
    return BY_KEY[key]


async def load():
    """Read overrides from the database into the cache. Called at startup."""
    global _cache
    values = {d.key: d.default for d in DEFINITIONS}
    try:
        stored = await setting_repository.get_all()
    except Exception as e:
        # Never let a settings problem stop the bot; fall back to defaults.
        logger.warning("Could not load settings, using defaults: %s", e)
        _cache = values
        return values

    for key, raw in stored.items():
        found = BY_KEY.get(key)
        if not found:
            continue  # a setting that was removed from the code
        try:
            values[key] = found.deserialize(raw)
        except Exception as e:
            logger.warning("Ignoring bad stored value for %s (%r): %s", key, raw, e)
    _cache = values
    return values


def get(key: str):
    """Current value, falling back to the default if settings aren't loaded yet."""
    if _cache is None:
        return BY_KEY[key].default
    return _cache.get(key, BY_KEY[key].default)


async def set(key: str, value, updated_by: str | None = None):
    found = BY_KEY[key]
    await setting_repository.set(key, found.serialize(value), updated_by=updated_by)
    if _cache is not None:
        _cache[key] = value
    logger.info("Setting %s changed to %r by %s", key, value, updated_by)


def current_values() -> list[tuple[SettingDef, object]]:
    return [(d, get(d.key)) for d in DEFINITIONS]
