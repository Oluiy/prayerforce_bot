"""Environment-based settings.

This is the only module that reads environment variables. Everything else
imports `settings` from here instead of calling os.getenv / load_dotenv.
"""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Read-only: values in bot/.env are loaded into the process environment.
load_dotenv(BASE_DIR / ".env")

DEFAULT_GSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "13TBoRvSj-0Vpc0-WQQYNYbnZa-ywzQ9dBanszT9KMvk/edit?usp=sharing"
)


def _parse_admin_ids(*raw_values: str) -> tuple[int, ...]:
    """Parse comma-separated Telegram user IDs, keeping order and dropping duplicates."""
    ids: list[int] = []
    for raw in raw_values:
        for part in raw.split(","):
            part = part.strip()
            if part.isdigit() and int(part) not in ids:
                ids.append(int(part))
    return tuple(ids)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str | None
    google_api_key: str | None
    admin_ids: tuple[int, ...]
    gsheet_url: str

    @property
    def primary_admin_id(self) -> int | None:
        """The first admin listed in ADMIN_IDS (then ADMIN_ID)."""
        return self.admin_ids[0] if self.admin_ids else None


settings = Settings(
    telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", ""), os.getenv("ADMIN_ID", "")),
    gsheet_url=os.getenv("GSHEET_URL", DEFAULT_GSHEET_URL),
)
