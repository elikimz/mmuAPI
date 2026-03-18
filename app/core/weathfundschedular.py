"""
WealthFund Scheduler
====================
Runs two background tasks on a fixed interval:
  1. update_daily_interest  – accrues daily interest for all active funds
  2. complete_matured_funds – settles funds that have reached their end_date,
                              credits the wallet, and records the income transaction.

Production schedule: every 60 minutes (configurable via WEALTHFUND_SCHEDULER_INTERVAL_MINUTES).

Fix (Startup Race Condition):
  The original code used next_run_time=datetime.utcnow() which fires the job
  immediately at startup, before the FastAPI application event loop and database
  connection pool are fully initialised. This caused the first scheduler tick to
  fail silently and could trigger complete_matured_funds multiple times if the
  app restarted rapidly.

  Fix: delay the first run by WEALTHFUND_SCHEDULER_STARTUP_DELAY_SECONDS (default 30s)
  to ensure the app is fully ready before the first tick.
"""

import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database.database import AsyncSessionLocal
from app.routers.userweathfund import complete_matured_funds, update_daily_interest

logger = logging.getLogger("mmuAPI.scheduler")

scheduler = AsyncIOScheduler()

# Allow the interval and startup delay to be tuned via environment variables
_INTERVAL_MINUTES = int(os.getenv("WEALTHFUND_SCHEDULER_INTERVAL_MINUTES", "60"))
_STARTUP_DELAY_SECONDS = int(os.getenv("WEALTHFUND_SCHEDULER_STARTUP_DELAY_SECONDS", "30"))


async def run_wealthfund_tasks():
    """
    Opens a fresh database session, runs both scheduled tasks, then closes it.
    Errors in one task do not prevent the other from running.
    """
    run_at = datetime.utcnow()
    logger.info(f"WealthFund scheduler tick at {run_at.isoformat()} UTC")

    async with AsyncSessionLocal() as db:
        try:
            await update_daily_interest(db)
        except Exception as exc:
            logger.error(f"update_daily_interest failed: {exc}", exc_info=True)

        try:
            await complete_matured_funds(db)
        except Exception as exc:
            logger.error(f"complete_matured_funds failed: {exc}", exc_info=True)

    logger.info(
        f"WealthFund scheduler tick complete "
        f"(took {(datetime.utcnow() - run_at).total_seconds():.2f}s)"
    )


def start_scheduler():
    """
    Starts the APScheduler background scheduler.
    Runs every WEALTHFUND_SCHEDULER_INTERVAL_MINUTES minutes (default 60).
    First run is delayed by WEALTHFUND_SCHEDULER_STARTUP_DELAY_SECONDS (default 30s)
    to avoid a race condition where the scheduler fires before the app is fully ready.
    """
    first_run_time = datetime.utcnow() + timedelta(seconds=_STARTUP_DELAY_SECONDS)

    scheduler.add_job(
        run_wealthfund_tasks,
        trigger="interval",
        minutes=_INTERVAL_MINUTES,
        next_run_time=first_run_time,       # delayed startup — avoids race condition
        id="wealthfund_tasks",
        replace_existing=True,
        max_instances=1,                    # prevent overlapping runs
        coalesce=True,                      # collapse missed runs into one
    )
    scheduler.start()
    logger.info(
        f"WealthFund scheduler started — interval: every {_INTERVAL_MINUTES} minute(s). "
        f"First run in {_STARTUP_DELAY_SECONDS}s at {first_run_time.isoformat()} UTC."
    )
