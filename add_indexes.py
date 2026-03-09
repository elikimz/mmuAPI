
import asyncio
from sqlalchemy import text
from app.database.database import engine

async def add_indexes():
    async with engine.begin() as conn:
        # Add indexes to frequently queried foreign keys and sort columns
        queries = [
            "CREATE INDEX IF NOT EXISTS idx_referrals_referrer_id ON referrals(referrer_id);",
            "CREATE INDEX IF NOT EXISTS idx_referrals_referred_id ON referrals(referred_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_tasks_user_id ON user_tasks(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_tasks_pending_user_id ON user_tasks_pending(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_tasks_completed_user_id ON user_tasks_completed(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_levels_user_id ON user_levels(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_user_wealthfunds_user_id ON user_wealthfunds(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_deposits_user_id ON deposits(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_withdrawals_user_id ON withdrawals(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_deposits_created_at ON deposits(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_withdrawals_created_at ON withdrawals(created_at);",
        ]
        for query in queries:
            try:
                await conn.execute(text(query))
                print(f"Executed: {query}")
            except Exception as e:
                print(f"Error executing {query}: {e}")

if __name__ == "__main__":
    asyncio.run(add_indexes())
