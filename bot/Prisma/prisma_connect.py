import asyncio
from prisma import Prisma

db = Prisma()

async def connect_db():
    await db.connect()
    print("Prisma client connected successfully")


if __name__ == "__main__":
    asyncio.run(connect_db())
    