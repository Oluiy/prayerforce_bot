"""Small, pure text-formatting helpers."""

MEDALS = ["🥇", "🥈", "🥉"]


def format_duration(total_seconds: int) -> str:
    minutes, seconds = divmod(max(0, int(total_seconds)), 60)
    return f"{minutes} min {seconds} sec"


def format_hours_minutes(total_seconds: int) -> str:
    return f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"


def rank_label(index: int) -> str:
    """Medal for the top three (0-based index), then "4.", "5.", ..."""
    return MEDALS[index] if index < len(MEDALS) else f"{index + 1}."


def full_name(user) -> str:
    return f"{user.firstName} {user.lastName}" if user.lastName else user.firstName
