
import asyncio
from app.database.database import AsyncSessionLocal
from app.models.models import User, Wallet, Level, UserLevel, Transaction, Task, UserTask, TransactionType
from sqlalchemy import select
from datetime import datetime

async def test_direct():
    async with AsyncSessionLocal() as db:
        # 1. Get level 17
        level = (await db.execute(select(Level).filter(Level.id == 17))).scalar_one()
        
        # 2. Create user
        user = User(number="+254700000000", country_code="+254", password="hash", referral_code="DIRECTTEST", is_admin=False)
        db.add(user)
        await db.flush()
        
        wallet = Wallet(user_id=user.id, balance=2000.0, income=0.0)
        db.add(wallet)
        await db.flush()
        
        print(f"Direct test for user {user.id} buying level {level.id}")
        
        # 3. Simulate buy_level logic
        wallet.balance -= level.earnest_money
        db.add(Transaction(user_id=user.id, type=TransactionType.LEVEL_PURCHASE.value, amount=level.earnest_money, created_at=datetime.utcnow()))
        
        user_level = UserLevel(
            user_id=user.id, level_id=level.id, name=level.name, description=level.description,
            earnest_money=level.earnest_money, workload=level.workload, salary=level.salary,
            daily_income=level.daily_income, monthly_income=level.monthly_income,
            annual_income=level.annual_income, created_at=datetime.utcnow()
        )
        db.add(user_level)
        
        tasks = (await db.execute(select(Task).filter(Task.level_id == level.id))).scalars().all()
        for t in tasks:
            db.add(UserTask(user_id=user.id, task_id=t.id, video_url=t.video_url, completed=False))
        
        await db.commit()
        print("✅ Direct DB commit successful")

if __name__ == "__main__":
    asyncio.run(test_direct())
