from telegram.ext import *
from Prisma.prisma_connect import *
from telegram.constants import ParseMode
from datetime import datetime, timezone

"""Send a message to all users when the bot starts"""
async def startup_broadcast(application: Application):
    users = await db.user.find_many()

    for user in users:
        try:
            message_text = (
                "🙏 Prayer Force Update 🙏\n\n"
                "We'll be going before the Lord by 5:30pm today with hearts ready to seek Him. "
                "Tell a Prayer Force member to tell a Prayer Force member to tell another Prayer Force member "
                "that today's meeting is not one you want to miss."
            )
            with open(
                "/Users/israel/Documents/prayerforce_bot/bot/handlers/prayer.jpg", "+rb"
            ) as photo:
                await application.bot.send_photo(
                    chat_id=user.chatId,
                    photo=photo,
                    caption=message_text,
                    parse_mode=ParseMode.MARKDOWN,
                )

        except Exception as e:
            print(f"Error sending message to {user.chatId}: {e}")


"""Temporal message Preconference Prayers"""
async def Broadcast(application: Application):
    users = await db.user.find_many()

    conference_date = datetime(2025, 6, 14, tzinfo=timezone.utc)  # Replace with actual date
    days_left = (conference_date - datetime.now(timezone.utc)).days
    print(days_left)

    for user in users:
        try:
            message = (
                "🙏 Preconference Prayers 🙏\n\n"
                f"{days_left} Days to Emerge Conference! \n\n"
                "Dear Prayer Force, we are called to pray for the upcoming conference.\n"
                "Join us in seeking God's guidance and blessings for this event.\n"
                "Remember, the conference is not for all prayer force members, "
            )
            with open(
                "/Users/israel/Documents/prayerforce_bot/bot/handlers/emerge.jpeg",
                "rb",
            ) as photo:
                await application.bot.send_photo(
                    chat_id=user.chatId,
                    photo=photo,
                    caption=message,
                    parse_mode=ParseMode.MARKDOWN,
                )

        except Exception as e:
            print(f"Error sending message to user {user.firstName} ({user.chatId}): {str(e)}")


"""Daily Recharge raminder to every user."""


async def daily_recharge(application: Application):
    users = await db.user.find_many()

    for user in users:
        try:
            message_text = (
                "Daily Recharge 🥰🙏 !!!\n\n"
                f"{user.firstName}, this is a personal reminder that we’ll be having our daily prayer meeting for just 30mins today from 7:00pm-7:30pm.\n"
                "Today's meeting is not one you want to miss"
            )
            await application.bot.send_message(chat_id=user.chatId, text=message_text)
        except Exception as e:
            print(f"Error sending message to {user.chatId}: {e}")


"""Love Letter raminder to every user."""


async def love_letter(application: Application):
    users = await db.user.find_many()
    for user in users:
        try:
            await application.bot.send_photo(
                chat_id=user.chatId, photo="", ParseMode=ParseMode.MARKDOWN
            )

        except Exception as e:
            print(f"Error sending message to {user.chatId}: {e}")
