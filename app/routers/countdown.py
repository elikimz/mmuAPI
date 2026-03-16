
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, time, timedelta
import pytz

from app.database.database import get_async_db
from app.models.models import User, UserLevel
from app.routers.auth import get_current_user
from app.schema.schema import CountdownResponse

router = APIRouter(prefix="/countdown", tags=["Countdown"])

# Kenya timezone (EAT = UTC+3)
KENYA_TZ = pytz.timezone("Africa/Nairobi")


@router.get("/me", response_model=CountdownResponse)
async def get_my_countdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Returns:
    - task_reset_seconds: seconds until midnight EAT (daily task reset)
    - level_expiry_seconds: seconds until the user's current level expires (None if no expiry)
    - level_name: name of the user's current level
    - has_expiry: True if the current level has an expiry date
    - intern_expiry_seconds: legacy field (same as level_expiry_seconds when level is 'Intern')
    - is_intern: legacy field (True when level name is 'Intern')
    """
    # 1. Task Reset Countdown — midnight EAT
    now_eat = datetime.now(KENYA_TZ)
    tomorrow_eat = now_eat + timedelta(days=1)
    midnight_eat = datetime.combine(tomorrow_eat.date(), time(0, 0, 0), tzinfo=KENYA_TZ)
    task_reset_seconds = int((midnight_eat - now_eat).total_seconds())

    # 2. Level Expiry Countdown — generic, based on expires_at column
    result = await db.execute(
        select(UserLevel).filter(UserLevel.user_id == current_user.id)
    )
    user_level = result.scalar_one_or_none()

    level_expiry_seconds = None
    level_name = None
    has_expiry = False
    is_intern = False
    intern_expiry_seconds = None

    if user_level:
        level_name = user_level.name
        is_intern = user_level.name.lower().strip() == "intern"

        if user_level.expires_at is not None:
            has_expiry = True
            now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
            expires_at_utc = (
                user_level.expires_at.replace(tzinfo=pytz.UTC)
                if user_level.expires_at.tzinfo is None
                else user_level.expires_at
            )
            remaining = (expires_at_utc - now_utc).total_seconds()
            level_expiry_seconds = max(0, int(remaining))
            if is_intern:
                intern_expiry_seconds = level_expiry_seconds

        elif is_intern:
            # Legacy fallback: intern levels created before the migration
            has_expiry = True
            created_at_utc = (
                user_level.created_at.replace(tzinfo=pytz.UTC)
                if user_level.created_at.tzinfo is None
                else user_level.created_at
            )
            expiry_time_utc = created_at_utc + timedelta(days=3)
            now_utc = datetime.now(pytz.UTC)
            remaining = (expiry_time_utc - now_utc).total_seconds()
            intern_expiry_seconds = max(0, int(remaining))
            level_expiry_seconds = intern_expiry_seconds

    return {
        "task_reset_seconds": task_reset_seconds,
        "level_expiry_seconds": level_expiry_seconds,
        "level_name": level_name,
        "has_expiry": has_expiry,
        # Legacy fields for backward compatibility
        "intern_expiry_seconds": intern_expiry_seconds,
        "is_intern": is_intern,
    }
