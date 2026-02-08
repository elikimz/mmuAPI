# import asyncio
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import update
# from datetime import datetime
# import pytz

# from app.database.database import get_async_db
# from app.models.models import UserTask

# # Kenya timezone
# KENYA_TZ = pytz.timezone("Africa/Nairobi")


# async def mark_all_tasks_completed():
#     """
#     Mark all user tasks as completed.
#     """
#     async for session in get_async_db():  # Use async generator for your session
#         try:
#             await session.execute(
#                 update(UserTask)
#                 .where(UserTask.completed == True)
#                 .values(completed=False)
#             )
#             await session.commit()
#             print(f"[{datetime.now(KENYA_TZ)}] All user tasks marked as incomplete.")
#         except Exception as e:
#             await session.rollback()
#             print(f"Error marking tasks completed: {e}")


# def start_task_scheduler():
#     """
#     Initialize and start the async scheduler.
#     """
#     scheduler = AsyncIOScheduler(timezone=KENYA_TZ)

#     # ✅ IMPORTANT: Pass the async function directly, do NOT wrap in create_task
#     scheduler.add_job(mark_all_tasks_completed, 'interval', seconds=5)

#     scheduler.start()
#     print("Task completion scheduler started (running every 5 seconds for testing).")



import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
from datetime import datetime
import pytz

from app.database.database import get_async_db
from app.models.models import UserTask

# Kenya timezone
KENYA_TZ = pytz.timezone("Africa/Nairobi")


async def mark_all_tasks_completed():
    """
    Marks all completed tasks as incomplete.
    """
    try:
        async for session in get_async_db():  # Use async generator for session
            result = await session.execute(
                update(UserTask)
                .where(UserTask.completed == True)  # completed → incomplete
                .values(completed=False)
            )
            await session.commit()
            print(
                f"[{datetime.now(KENYA_TZ)}] "
                f"{result.rowcount} completed tasks marked as incomplete."
            )
    except Exception as e:
        await session.rollback()
        print(f"[{datetime.now(KENYA_TZ)}] Error updating tasks: {e}")


def start_task_scheduler():
    """
    Initialize and start the async scheduler.
    """
    scheduler = AsyncIOScheduler(timezone=KENYA_TZ)

    # ✅ Schedule the job to run daily at 12:00 AM Kenya time
    scheduler.add_job(
        mark_all_tasks_completed,
        trigger='cron',
        hour=0,
        minute=0,
        second=0
    )

    scheduler.start()
    print(f"[{datetime.now(KENYA_TZ)}] Task completion scheduler started (runs daily at 12:00 AM).")
