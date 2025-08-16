from telegram import Update

async def getchatID(update: Update):
    chat_id = await update.effective_chat.id
    return chat_id

async def getfirstName(update: Update):
    first_name = await update.effective_user.first_name
    return first_name

async def getLastName(update: Update):
    last_name = await update.effective_user.last_name
    return last_name

async def user(update: Update):
    abt_user = await update.effective_user
    return abt_user

