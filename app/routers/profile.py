from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.database.database import get_async_db
from app.models.models import (
    User,
    Wallet,
    UserLevel,
    UserTask,
    UserTaskCompleted,
    UserTaskPending,
    UserWealthFund,
    Referral,
)
from app.routers.auth import get_current_user
from app.schema.schema import UserProfileResponse

router = APIRouter(prefix="/users", tags=["Users"])


# -------------------------
# USER: Profile
# -------------------------
@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Wallet
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == user.id)
    )
    wallet = wallet_result.scalar_one_or_none()

    # Levels
    levels_result = await db.execute(
        select(UserLevel).where(UserLevel.user_id == user.id)
    )
    levels = levels_result.scalars().all()

    # Tasks stats
    total_tasks = await db.scalar(
        select(func.count(UserTask.id)).where(UserTask.user_id == user.id)
    )

    completed_tasks = await db.scalar(
        select(func.count(UserTaskCompleted.id)).where(
            UserTaskCompleted.user_id == user.id
        )
    )

    pending_tasks = await db.scalar(
        select(func.count(UserTaskPending.id)).where(
            UserTaskPending.user_id == user.id
        )
    )

    # Referrals
    total_referrals = await db.scalar(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user.id
        )
    )

    active_referrals = await db.scalar(
        select(func.count(Referral.id)).where(
            Referral.referrer_id == user.id,
            Referral.is_active == True
        )
    )

    referral_bonus = await db.scalar(
        select(func.coalesce(func.sum(Referral.bonus_amount), 0)).where(
            Referral.referrer_id == user.id
        )
    )

    # Wealth funds
    wf_result = await db.execute(
        select(UserWealthFund).where(UserWealthFund.user_id == user.id)
    )
    wealthfunds = wf_result.scalars().all()

    return {
        "id": user.id,
        "number": user.number,
        "country_code": user.country_code,
        "referral_code": user.referral_code,
        "created_at": user.created_at,

        "wallet": wallet,

        "levels": [
            {
                "id": l.level_id,
                "name": l.name,
                "daily_income": l.daily_income,
                "monthly_income": l.monthly_income,
            }
            for l in levels
        ],

        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,

        "total_referrals": total_referrals,
        "active_referrals": active_referrals,
        "referral_bonus": referral_bonus,

        "wealthfunds": [
            {
                "id": wf.id,
                "name": wf.name,
                "amount": wf.amount,
                "total_profit": wf.total_profit,
                "status": wf.status,
            }
            for wf in wealthfunds
        ],
    }
