
import asyncio
from app.database.database import AsyncSessionLocal
from app.models.models import Level
from sqlalchemy import select

async def find():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Level).filter(Level.earnest_money > 0, Level.locked == False).limit(1))
        level = result.scalar_one_or_none()
        if level:
            print(f"FOUND_LEVEL_ID={level.id}")
            print(f"FOUND_LEVEL_NAME={level.name}")
            print(f"FOUND_LEVEL_PRICE={level.earnest_money}")
        else:
            print("NO_PAID_LEVEL_FOUND")

if __name__ == "__main__":
    asyncio.run(find())
