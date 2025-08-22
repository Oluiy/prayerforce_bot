from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

async def announcement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = (
        "<b> 📣📣📣 Prayer Force Announcements 📣📣📣 </b>\n\n"
        "1.<b>Daily Recharge: </b>Daily Recharge is a time to come fellowship with the Holy Spirit "
        "and to be recharged, It holds from <b>Monday through Friday</b>\texcept on Wednesdays due to "
        "Communion Service. Time is from <code>7:00pm - 7:30pm</code>.\n\n"
        "2.<b>Office Prayers: </b>Office Prayers holds every <b>Wednesday</b> from <code>5:15pm - 5:45</code>"
        " before Communion Service.\n\n"
        "3.<b>Get Edified: </b>We\'ll be going before the Lord by 5:30pm today with hearts ready to seek Him. "
        "Tell a Prayer Force member to tell a Prayer Force member to tell another Prayer Force member "
        "that today's meeting is not one you want to miss.\n\n"
        "4.<b>WeekDay Chapel Service: </b> <code>Tuesday and Thursday Service -> 7:00am - 7:30am</code>\n\n" 
        "5.<b>Sunday Service: </b><code>Pre-service ->7:15am - 7:45am</code>\n" 
        "<code>Post-service ->8:15am - 8:45am</code>"
    )
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message_text,
        parse_mode="HTML" # Use HTML for formatting
    )
    
annoucement_handler = CommandHandler("announcement", announcement)