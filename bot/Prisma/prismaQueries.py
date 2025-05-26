from Prisma.prisma_connect import * 
from telegram import * 

user = Update.effective_user

async def find_user(update: Update):
    await db.user.find_unique(
        where={"chatId": str(user.id)}
    )


async def find_all_user():
    users = await db.user.find_many()

    
