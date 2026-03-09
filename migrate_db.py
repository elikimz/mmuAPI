
import asyncio
from sqlalchemy import text
from app.database.database import engine

async def migrate():
    async with engine.begin() as conn:
        print("Checking for created_at column in user_levels table...")
        # Check if column exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='user_levels' AND column_name='created_at';
        """))
        if not result.fetchone():
            print("Adding created_at column to user_levels...")
            await conn.execute(text("ALTER TABLE user_levels ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
            print("Column added successfully.")
        else:
            print("Column created_at already exists.")

if __name__ == "__main__":
    asyncio.run(migrate())
