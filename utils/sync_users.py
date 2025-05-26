import asyncio
from datetime import datetime
from bot.Prisma.prisma_connect import db
# from modules.sheet_service import fetch_sheet_data
from validate_data import validate_entries

async def sync_users():
    await db.connect()
    sheet_data = fetch_sheet_data()
    valid_users = validate_entries(sheet_data)

    for entry in valid_users:
        chat_id = entry["ChatId"]
        first_name = entry["FirstName"]
        last_name = entry["LastName"]
        birthday = datetime.strptime(entry["Birthday"], "%Y-%m-%d")

        existing = await db.user.find_unique(where={"chatId": chat_id})
        if not existing:
            await db.user.create(
                data={
                    "chatId": str(chat_id),
                    "firstName": first_name,
                    "lastName": last_name,
                    "birthday": birthday
                }
            )

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(sync_users())
