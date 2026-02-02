# # app/scheduler.py

# from datetime import datetime
# from sqlalchemy.ext.asyncio import AsyncSession
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from app.database.database import AsyncSessionLocal
# from app.routers.userweathfund import complete_matured_funds, update_daily_interest  # ✅ use your existing sessionmaker

# scheduler = AsyncIOScheduler()

# async def run_update_tasks():
#     # Create a new AsyncSession for the scheduler
#     async with AsyncSessionLocal() as db:  
#         await update_daily_interest(db)
#         await complete_matured_funds(db)

# def start_scheduler():
#     """
#     Starts APScheduler to run the wealth fund updates automatically every day at midnight UTC
#     """
#     # Run daily at midnight
#     scheduler.add_job(run_update_tasks, 'cron', hour=0, minute=0)
#     scheduler.start()
#     print("✅ Wealth fund scheduler started")



# app/scheduler.py

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.database.database import AsyncSessionLocal
from app.routers.userweathfund import complete_matured_funds, update_daily_interest

scheduler = AsyncIOScheduler()

async def run_update_tasks():
    # Create a new AsyncSession for the scheduler
    async with AsyncSessionLocal() as db:
        await update_daily_interest(db)
        await complete_matured_funds(db)
        print(f"✅ Wealth fund tasks run at {datetime.utcnow()}")  # log for testing

def start_scheduler():
    """
    Starts APScheduler to run the wealth fund updates every 5 hours (testing)
    """
    # Run every 5 hours for testing
    scheduler.add_job(run_update_tasks, 'interval', hours=5)
    scheduler.start()
    print("✅ Wealth fund scheduler started (testing every 5 hours)")