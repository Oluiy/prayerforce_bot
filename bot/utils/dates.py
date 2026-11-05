"""Date and time helpers. All admin-facing times are read and shown in TIMEZONE."""
import datetime
import re

from config.constants import TIMEZONE


def utc_now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def local_now() -> datetime.datetime:
    return datetime.datetime.now(TIMEZONE)


def is_last_day_of_month(day: datetime.datetime) -> bool:
    return (day + datetime.timedelta(days=1)).month != day.month


def to_local(moment: datetime.datetime) -> datetime.datetime:
    """Show a stored (UTC) time in the local timezone."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=datetime.timezone.utc)
    return moment.astimezone(TIMEZONE)


def to_utc(moment: datetime.datetime) -> datetime.datetime:
    """Store a local time as UTC. Naive input is assumed to be local."""
    if moment.tzinfo is None:
        moment = TIMEZONE.localize(moment)
    return moment.astimezone(datetime.timezone.utc)


class TimeParseError(ValueError):
    """The admin typed something we can't read as a date/time."""


_RELATIVE = re.compile(r"^\+\s*(\d+)\s*(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)$", re.I)
_CLOCK = re.compile(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)?$", re.I)
_DATED = re.compile(r"^(\d{4})-(\d{2})-(\d{2})[\s,]+(.+)$")


def _clock_to_time(text: str) -> datetime.time:
    match = _CLOCK.match(text.strip())
    if not match:
        raise TimeParseError(f"Not a time: {text!r}")
    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    suffix = (match.group(3) or "").lower()

    if suffix == "pm" and hour != 12:
        hour += 12
    elif suffix == "am" and hour == 12:
        hour = 0
    elif not suffix and hour > 23:
        raise TimeParseError(f"Hour out of range: {text!r}")

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise TimeParseError(f"Time out of range: {text!r}")
    return datetime.time(hour, minute)


def parse_when(text: str, now: datetime.datetime | None = None) -> datetime.datetime:
    """Read an admin-typed moment and return it as an aware UTC datetime.

    Accepted forms (times are local):
      "now"                     -> right now
      "+2h", "+30m", "+1d"      -> relative to now
      "8pm", "20:00", "8:30 PM" -> that clock time, today if still ahead, else tomorrow
      "tomorrow 8pm"            -> that clock time tomorrow
      "2026-11-09 19:30"        -> an exact date and time
    """
    raw = (text or "").strip()
    if not raw:
        raise TimeParseError("Nothing to read.")

    now = now or local_now()
    lowered = raw.lower()

    if lowered in {"now", "immediately"}:
        return to_utc(now)

    relative = _RELATIVE.match(lowered)
    if relative:
        amount, unit = int(relative.group(1)), relative.group(2).lower()
        if unit.startswith("m"):
            delta = datetime.timedelta(minutes=amount)
        elif unit.startswith("h"):
            delta = datetime.timedelta(hours=amount)
        else:
            delta = datetime.timedelta(days=amount)
        return to_utc(now + delta)

    dated = _DATED.match(raw)
    if dated:
        year, month, day, rest = dated.groups()
        clock = _clock_to_time(rest)
        try:
            naive = datetime.datetime(int(year), int(month), int(day), clock.hour, clock.minute)
        except ValueError as e:
            raise TimeParseError(str(e)) from e
        return to_utc(naive)

    day_offset = 0
    for prefix, offset in (("tomorrow", 1), ("today", 0), ("tonight", 0)):
        if lowered.startswith(prefix):
            day_offset = offset
            raw = raw[len(prefix):].strip() or "9pm"
            break

    clock = _clock_to_time(raw)
    target = (now + datetime.timedelta(days=day_offset)).replace(
        hour=clock.hour, minute=clock.minute, second=0, microsecond=0
    )
    # A bare clock time means the next time it comes round.
    if day_offset == 0 and target <= now and not lowered.startswith(("today", "tonight")):
        target += datetime.timedelta(days=1)
    return to_utc(target)


def format_moment(moment: datetime.datetime, now: datetime.datetime | None = None) -> str:
    """Friendly local description, e.g. "today at 11:00 PM" or "Sat 6 Dec, 8:00 AM"."""
    local = to_local(moment)
    now = now or local_now()
    clock = local.strftime("%I:%M %p").lstrip("0")

    days_ahead = (local.date() - now.date()).days
    if days_ahead == 0:
        return f"today at {clock}"
    if days_ahead == 1:
        return f"tomorrow at {clock}"
    if 2 <= days_ahead <= 6:
        return f"{local.strftime('%A')} at {clock}"
    return f"{local.strftime('%a %-d %b')}, {clock}"
