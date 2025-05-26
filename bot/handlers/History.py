import telegram
from telegram import Update
from telegram.ext import ContextTypes


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="BRIEF HISTORY OF PRAYER FORCE COVENANT UNIVERSITYSeun Durand now pastor Seun Durand was the successor after Brother Dare. He fought fiercely to see that Prayer conference continued having been suspended for about eight months due to increase in school activities. He and his team made the constitution for the executives of Prayer force. He initiated a program “tarry in His presence” where certain people would come into the office and begin praying till the Holy Ghost says its enough. The present prayer force office was gotten at this period too.",
    )

    # Fetch the user's history from the databas
