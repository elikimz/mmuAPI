"""
WealthFund Scheduler
====================
Runs two background tasks on a fixed interval:
  1. update_daily_interest  – accrues daily interest for all active funds
  2. complete_matured_funds – settles funds that have reached their end_date,
                              credits the wallet, and records the income transaction.

Production schedule: every 60 minutes (configurable via WEALTHFUND_SCHEDULER_INTERVAL_MINUTES).
This ensures matured funds are processed within at most one hour of their end_date,
without hammering the database.
"""

import logging
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database.database import AsyncSessionLocal
from app.routers.userweathfund import complete_matured_funds, update_daily_interest

logger = logging.getLogger("mmuAPI.scheduler")

scheduler = AsyncIOScheduler()

# Allow the interval to be tuned via environment variable (default: 60 minutes)
_INTERVAL_MINUTES = int(os.getenv("WEALTHFUND_SCHEDULER_INTERVAL_MINUTES", "60"))


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
    Also fires once immediately at startup so that any funds that matured
    while the server was offline are settled right away.
    """
    scheduler.add_job(
        run_wealthfund_tasks,
        trigger="interval",
        minutes=_INTERVAL_MINUTES,
        next_run_time=datetime.utcnow(),   # fire immediately on startup
        id="wealthfund_tasks",
        replace_existing=True,
        max_instances=1,                    # prevent overlapping runs
        coalesce=True,                      # collapse missed runs into one
    )
    scheduler.start()
    logger.info(
        f"WealthFund scheduler started — interval: every {_INTERVAL_MINUTES} minute(s). "
        f"First run: immediate."
    )
