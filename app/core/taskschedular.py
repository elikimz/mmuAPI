
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete, select
from datetime import datetime, timedelta
import pytz

from app.database.database import get_async_db
# Models are imported inside functions to prevent circular dependency

# Kenya timezone
KENYA_TZ = pytz.timezone("Africa/Nairobi")


async def reset_daily_tasks():
    """
    Marks all completed tasks as incomplete and clears history for the new day.
    Runs daily at midnight Kenya time.
    """
    from app.models.models import UserTask
    try:
        async for session in get_async_db():
            # 1. Reset completion status in UserTask
            result = await session.execute(
                update(UserTask)
                .where(UserTask.completed == True)
                .values(completed=False)
            )
            
            # 2. Optional: Clear daily history if needed (UserTaskCompleted/Pending)
            # For this system, we keep them but the 'completed' flag in UserTask 
            # is what controls if the user can do the task again today.
            
            await session.commit()
            print(
                f"[{datetime.now(KENYA_TZ)}] Daily Reset: "
                f"{result.rowcount} tasks reset for the new day."
            )
    except Exception as e:
        print(f"[{datetime.now(KENYA_TZ)}] Error in daily reset: {e}")


async def expire_intern_levels():
    """
    Expires 'Intern' levels after 3 days from purchase.
    """
    from app.models.models import UserTask, UserLevel
    try:
        async for session in get_async_db():
            # Model created_at is UTC
            expiry_time = datetime.utcnow() - timedelta(days=3)
            
            # Find intern levels that are older than 3 days
            result = await session.execute(
                select(UserLevel)
                .filter(UserLevel.name.ilike("intern"))
                .filter(UserLevel.created_at <= expiry_time)
            )
            expired_levels = result.scalars().all()
            
            if expired_levels:
                count = len(expired_levels)
                for level in expired_levels:
                    # Remove associated tasks for this user
                    await session.execute(
                        delete(UserTask)
                        .where(UserTask.user_id == level.user_id)
                    )
                    # Remove the level
                    await session.delete(level)
                
                await session.commit()
                print(f"[{datetime.now(KENYA_TZ)}] Level Expiry: {count} intern levels expired.")
    except Exception as e:
        print(f"[{datetime.now(KENYA_TZ)}] Error in level expiry: {e}")


def start_task_scheduler():
    """
    Initialize and start the async scheduler.
    """
    scheduler = AsyncIOScheduler(timezone=KENYA_TZ)

    # 1. Schedule Task Reset at Midnight EAT
    scheduler.add_job(
        reset_daily_tasks,
        trigger='cron',
        hour=0,
        minute=0,
        second=0
    )

    # 2. Schedule Intern Level Expiry (Check every hour)
    scheduler.add_job(
        expire_intern_levels,
        trigger='interval',
        hours=1
    )

    scheduler.start()
    print(f"[{datetime.now(KENYA_TZ)}] Scheduler started: Daily Reset (00:00 EAT) & Intern Expiry (Hourly check).")
