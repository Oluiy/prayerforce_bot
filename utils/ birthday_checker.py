import asyncio
from datetime import datetime
from bot.Prisma.prisma_connect import db
from bot.handlers.birthdaymessage import send_birthday_message

async def check_birthdays():
    await db.connect()
    today = datetime.now().date()

    birthday_users = await db.user.find_many(
        where={
            "birthday": {
                "equals": today
            }
        }
    )

    for user in birthday_users:
        mates = [u for u in birthday_users if u.chatId != user.chatId]
        await send_birthday_message(user, mates)

    await db.disconnect()
