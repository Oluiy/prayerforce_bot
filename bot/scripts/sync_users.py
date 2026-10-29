"""Import members from the Google Sheet. Run from the bot/ folder: python -m scripts.sync_users"""
import asyncio
from datetime import datetime

from database.prisma_connect import db
from repositories import user_repository
from services.sheets_service import fetch_sheet_data
from utils.validation import validate_entries


async def sync_users():
    await db.connect()
    try:
        for entry in validate_entries(fetch_sheet_data()):
            chat_id = entry["ChatId"]
            if not await user_repository.get_by_chat_id(chat_id):
                await user_repository.create(
                    chat_id,
                    entry["FirstName"],
                    entry["LastName"],
                    birthday=datetime.strptime(entry["Birthday"], "%Y-%m-%d"),
                )
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(sync_users())
