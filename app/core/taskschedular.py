"""
Task Scheduler — runs two recurring jobs:

1. reset_daily_tasks()    — midnight EAT: resets all user tasks for the new day
                            (only for ACTIVE user levels; skips expired levels)
2. expire_user_levels()   — every 5 minutes: marks UserLevel + UserTask records
                            as 'expired' when expires_at has passed.
                            Uses database state as source of truth — does NOT
                            delete records so history is preserved.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import update, delete, select
from datetime import datetime, timedelta
import pytz

from app.database.database import get_async_db

# Kenya timezone
KENYA_TZ = pytz.timezone("Africa/Nairobi")


async def expire_user_levels():
    """
    Runs every 5 minutes.

    Finds all UserLevel records where:
        expires_at < now  AND  status = 'active'

    For each such level:
        1. Mark UserLevel.status → 'expired'
        2. Mark all UserTask records for that user → status = 'expired'
           (tasks are NOT deleted — history is preserved)

    Legacy fallback: intern levels without expires_at that are older than 3 days
    are also expired via the same status-update path.

    This ensures expiry is enforced even when users are offline.
    """
    from app.models.models import UserTask, UserLevel
    try:
        async for session in get_async_db():
            now_utc = datetime.utcnow()

            # ── Primary path: levels with an explicit expires_at ──────────
            result = await session.execute(
                select(UserLevel).filter(
                    UserLevel.expires_at.isnot(None),
                    UserLevel.expires_at <= now_utc,
                    UserLevel.status == "active",
                )
            )
            expired_levels = result.scalars().all()

            # ── Legacy fallback: intern levels without expires_at > 3 days ─
            legacy_cutoff = now_utc - timedelta(days=3)
            legacy_result = await session.execute(
                select(UserLevel).filter(
                    UserLevel.expires_at.is_(None),
                    UserLevel.name.ilike("intern"),
                    UserLevel.created_at <= legacy_cutoff,
                    UserLevel.status == "active",
                )
            )
            legacy_levels = legacy_result.scalars().all()

            all_expired = expired_levels + legacy_levels

            if all_expired:
                for level in all_expired:
                    # 1. Mark the level itself as expired
                    level.status = "expired"
                    session.add(level)

                    # 2. Mark all UserTask records for this user as expired
                    await session.execute(
                        update(UserTask)
                        .where(UserTask.user_id == level.user_id)
                        .values(status="expired")
                    )

                    # 3. Notify the user via WebSocket so the frontend can invalidate caches
                    try:
                        from app.core.websocket_manager import manager
                        from app.core.redis_cache import cache
                        await cache.delete(f"user_profile_{level.user_id}")
                        await manager.send_personal_message(level.user_id, {
                            "type": "LEVEL_EXPIRED",
                            "level_id": level.level_id,
                            "level_name": level.name,
                        })
                    except Exception as comm_e:
                        print(f"Warning: Post-expiry communication failed for user {level.user_id}: {comm_e}")

                await session.commit()
                print(
                    f"[{datetime.now(KENYA_TZ)}] Level Expiry: "
                    f"{len(all_expired)} level(s) marked expired "
                    f"({len(expired_levels)} via expires_at, "
                    f"{len(legacy_levels)} via legacy intern rule). "
                    f"Associated UserTask records marked expired."
                )
            else:
                print(f"[{datetime.now(KENYA_TZ)}] Level Expiry: No newly expired levels found.")

    except Exception as e:
        print(f"[{datetime.now(KENYA_TZ)}] ERROR in expire_user_levels: {e}")
        import traceback
        print(traceback.format_exc())


async def reset_daily_tasks():
    """
    Runs daily at midnight EAT.

    For each user that has an ACTIVE UserLevel (status = 'active'):
      1. Identify which task IDs belong to the user's CURRENT level.
      2. Delete any UserTask records for that user whose task does NOT belong
         to the current level (stale tasks from a previous level).
      3. Reset completion flags on remaining ACTIVE tasks.
      4. Clear UserTaskPending and UserTaskCompleted tables for active users.
      5. Ensure every task for the current level is assigned (idempotent).

    Expired levels are explicitly SKIPPED — their tasks are not reset.
    """
    from app.models.models import UserTask, UserTaskPending, UserTaskCompleted, UserLevel, Task
    try:
        async for session in get_async_db():
            # Fetch only ACTIVE user levels
            user_levels_result = await session.execute(
                select(UserLevel).filter(UserLevel.status == "active")
            )
            user_levels = user_levels_result.scalars().all()

            active_user_ids = [ul.user_id for ul in user_levels]

            # Clear pending and completed history only for active users
            if active_user_ids:
                await session.execute(
                    delete(UserTaskPending).where(
                        UserTaskPending.user_id.in_(active_user_ids)
                    )
                )
                await session.execute(
                    delete(UserTaskCompleted).where(
                        UserTaskCompleted.user_id.in_(active_user_ids)
                    )
                )

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

                # 2b. Reset completion flags on valid ACTIVE tasks
                reset_result = await session.execute(
                    update(UserTask)
                    .where(
                        UserTask.user_id == ul.user_id,
                        UserTask.task_id.in_(valid_task_ids),
                        UserTask.completed == True,
                        UserTask.status == "active",
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
                        task_obj = await session.get(Task, task_id)
                        if task_obj:
                            session.add(UserTask(
                                user_id=ul.user_id,
                                task_id=task_id,
                                video_url=task_obj.video_url,
                                completed=False,
                                status="active",
                            ))
                            new_tasks_count += 1

            await session.commit()
            print(
                f"[{datetime.now(KENYA_TZ)}] Daily Reset (active levels only): "
                f"{reset_count} tasks reset, "
                f"{purged_count} stale tasks purged, "
                f"{new_tasks_count} new task assignments created."
            )
    except Exception as e:
        print(f"[{datetime.now(KENYA_TZ)}] ERROR in reset_daily_tasks: {e}")
        import traceback
        print(traceback.format_exc())


def start_task_scheduler():
    """
    Initialises and starts the APScheduler async scheduler.
    Jobs:
      - Level expiry check every 5 minutes (marks status = 'expired')
      - Daily task reset at midnight EAT (active levels only)
    """
    scheduler = AsyncIOScheduler(timezone=KENYA_TZ)

    # Delay the first run of interval jobs to avoid startup race conditions
    import os
    startup_delay = int(os.getenv("TASK_SCHEDULER_STARTUP_DELAY_SECONDS", "30"))
    first_run_time = datetime.now(KENYA_TZ) + timedelta(seconds=startup_delay)

    # 1. Level expiry check every 5 minutes
    scheduler.add_job(
        expire_user_levels,
        trigger="interval",
        minutes=5,
        next_run_time=first_run_time,
        id="level_expiry_check",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # 2. Daily task reset at midnight EAT
    scheduler.add_job(
        reset_daily_tasks,
        trigger="cron",
        hour=0,
        minute=0,
        second=0,
        id="daily_task_reset",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    scheduler.start()
    print(
        f"[{datetime.now(KENYA_TZ)}] Scheduler started: "
        f"Level Expiry (every 5 min, first run in {startup_delay}s) & Daily Reset (00:00 EAT, active levels only)."
    )
