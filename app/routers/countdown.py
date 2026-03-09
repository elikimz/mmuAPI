
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, time, timedelta
import pytz
from typing import Optional

from app.database.database import get_async_db
from app.models.models import User, UserLevel
from app.routers.auth import get_current_user
from app.schema.schema import CountdownResponse

router = APIRouter(prefix="/countdown", tags=["Countdown"])

# Kenya timezone
KENYA_TZ = pytz.timezone("Africa/Nairobi")

@router.get("/me", response_model=CountdownResponse)
async def get_my_countdown(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 1. Calculate Task Reset Countdown (Midnight EAT)
    now_eat = datetime.now(KENYA_TZ)
    tomorrow_eat = now_eat + timedelta(days=1)
    midnight_eat = datetime.combine(tomorrow_eat.date(), time(0, 0, 0), tzinfo=KENYA_TZ)
    task_reset_seconds = int((midnight_eat - now_eat).total_seconds())

    # 2. Calculate Intern Level Expiry Countdown
    # Find if user has an 'Intern' level
    result = await db.execute(
        select(UserLevel)
        .filter(UserLevel.user_id == current_user.id)
        .filter(UserLevel.name.ilike("intern"))
    )
    intern_level = result.scalar_one_or_none()

    intern_expiry_seconds = None
    is_intern = False
    
    if intern_level:
        is_intern = True
        # Ensure created_at has tzinfo or compare in UTC
        # Model created_at is UTC by default
        created_at_utc = intern_level.created_at.replace(tzinfo=pytz.UTC)
        expiry_time_utc = created_at_utc + timedelta(days=3)
        now_utc = datetime.now(pytz.UTC)
        
        remaining = (expiry_time_utc - now_utc).total_seconds()
        intern_expiry_seconds = max(0, int(remaining))

    return {
        "task_reset_seconds": task_reset_seconds,
        "intern_expiry_seconds": intern_expiry_seconds,
        "is_intern": is_intern
    }
