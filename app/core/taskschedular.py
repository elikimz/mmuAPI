"""
Task Scheduler — runs two recurring jobs:

1. reset_daily_tasks()    — midnight EAT: resets all user tasks for the new day
2. expire_user_levels()   — hourly: removes user levels whose expires_at has passed
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import update, delete, select
from datetime import datetime, timedelta
import pytz

from app.database.database import get_async_db

# Kenya timezone
KENYA_TZ = pytz.timezone("Africa/Nairobi")


async def reset_daily_tasks():
    """
    Runs daily at midnight EAT.

    For each user that has an active UserLevel:
      1. Identify which task IDs belong to the user's CURRENT level.
      2. Delete any UserTask records for that user whose task does NOT belong
         to the current level (stale tasks from a previous level).
      3. Reset completion flags on remaining tasks.
      4. Clear UserTaskPending and UserTaskCompleted tables.
      5. Ensure every task for the current level is assigned (idempotent).

    This guarantees that even if a stale task somehow survived an upgrade,
    the nightly reset will clean it up.
    """
    from app.models.models import UserTask, UserTaskPending, UserTaskCompleted, UserLevel, Task
    try:
        async for session in get_async_db():
            # 1. Clear pending and completed history for the new day
            await session.execute(delete(UserTaskPending))
            await session.execute(delete(UserTaskCompleted))

            # 2. Process each active user level
            user_levels_result = await session.execute(select(UserLevel))
            user_levels = user_levels_result.scalars().all()

            reset_count = 0
            purged_count = 0
            new_tasks_count = 0

            for ul in user_levels:
                # Fetch the valid task IDs for this user's current level
                valid_tasks_result = await session.execute(
                    select(Task.id).filter(Task.level_id == ul.level_id)
                )
                valid_task_ids = [row[0] for row in valid_tasks_result.fetchall()]

                if not valid_task_ids:
                    # Level has no tasks — remove any orphaned user tasks
                    purge_result = await session.execute(
                        delete(UserTask).where(UserTask.user_id == ul.user_id)
                    )
                    purged_count += purge_result.rowcount
                    continue

                # 2a. Remove stale tasks (tasks NOT belonging to the current level)
                purge_result = await session.execute(
                    delete(UserTask).where(
                        UserTask.user_id == ul.user_id,
                        UserTask.task_id.notin_(valid_task_ids),
                    )
                )
                purged_count += purge_result.rowcount

                # 2b. Reset completion flags on valid tasks
                reset_result = await session.execute(
                    update(UserTask)
                    .where(
                        UserTask.user_id == ul.user_id,
                        UserTask.task_id.in_(valid_task_ids),
                        UserTask.completed == True,
                    )
                    .values(completed=False)
                )
                reset_count += reset_result.rowcount

                # 2c. Assign any missing tasks for the current level (idempotent)
                for task_id in valid_task_ids:
                    existing = await session.execute(
                        select(UserTask).filter(
                            UserTask.user_id == ul.user_id,
                            UserTask.task_id == task_id,
                        )
                    )
                    if not existing.scalar_one_or_none():
                        # Fetch full task to get video_url
                        task_obj = await session.get(Task, task_id)
                        if task_obj:
                            session.add(UserTask(
                                user_id=ul.user_id,
                                task_id=task_id,
                                video_url=task_obj.video_url,
                                completed=False,
                            ))
                            new_tasks_count += 1

            await session.commit()
            print(
                f"[{datetime.now(KENYA_TZ)}] Daily Reset: "
                f"{reset_count} tasks reset, "
                f"{purged_count} stale tasks purged, "
                f"{new_tasks_count} new task assignments created."
            )
    except Exception as e:
        print(f"[{datetime.now(KENYA_TZ)}] ERROR in reset_daily_tasks: {e}")
        import traceback
        print(traceback.format_exc())


async def expire_user_levels():
    """
    Runs hourly.
    Removes UserLevel records whose expires_at has passed, and deletes
    the associated UserTask records so the user loses access.

    Supports ALL levels generically — not just 'Intern'.
    Legacy fallback: if a level is named 'intern' and has no expires_at,
    it falls back to the original 3-day rule based on created_at.
    """
    from app.models.models import UserTask, UserTaskPending, UserTaskCompleted, UserLevel
    try:
        async for session in get_async_db():
            now_utc = datetime.utcnow()

            # Primary path: use expires_at column
            result = await session.execute(
                select(UserLevel).filter(
                    UserLevel.expires_at.isnot(None),
                    UserLevel.expires_at <= now_utc
                )
            )
            expired_levels = result.scalars().all()

            # Legacy fallback: intern levels without expires_at older than 3 days
            legacy_cutoff = now_utc - timedelta(days=3)
            legacy_result = await session.execute(
                select(UserLevel).filter(
                    UserLevel.expires_at.is_(None),
                    UserLevel.name.ilike("intern"),
                    UserLevel.created_at <= legacy_cutoff
                )
            )
            legacy_levels = legacy_result.scalars().all()

            all_expired = expired_levels + legacy_levels

            if all_expired:
                for level in all_expired:
                    # Remove all task records for this user on expiry
                    await session.execute(
                        delete(UserTaskPending).where(UserTaskPending.user_id == level.user_id)
                    )
                    await session.execute(
                        delete(UserTaskCompleted).where(UserTaskCompleted.user_id == level.user_id)
                    )
                    await session.execute(
                        delete(UserTask).where(UserTask.user_id == level.user_id)
                    )
                    await session.delete(level)

                await session.commit()
                print(
                    f"[{datetime.now(KENYA_TZ)}] Level Expiry: "
                    f"{len(all_expired)} level(s) expired and removed "
                    f"({len(expired_levels)} via expires_at, "
                    f"{len(legacy_levels)} via legacy intern rule)."
                )
            else:
                print(f"[{datetime.now(KENYA_TZ)}] Level Expiry: No expired levels found.")

    except Exception as e:
        print(f"[{datetime.now(KENYA_TZ)}] ERROR in expire_user_levels: {e}")
        import traceback
        print(traceback.format_exc())


def start_task_scheduler():
    """
    Initialises and starts the APScheduler async scheduler.
    Jobs:
      - Daily task reset at midnight EAT
      - Hourly level expiry check
    """
    scheduler = AsyncIOScheduler(timezone=KENYA_TZ)

    # 1. Daily task reset at midnight EAT
    scheduler.add_job(
        reset_daily_tasks,
        trigger="cron",
        hour=0,
        minute=0,
        second=0,
        id="daily_task_reset",
        replace_existing=True,
    )

    # 2. Hourly level expiry check
    scheduler.add_job(
        expire_user_levels,
        trigger="interval",
        hours=1,
        id="level_expiry_check",
        replace_existing=True,
    )

    scheduler.start()
    print(
        f"[{datetime.now(KENYA_TZ)}] Scheduler started: "
        f"Daily Reset (00:00 EAT) & Level Expiry (hourly check)."
    )
