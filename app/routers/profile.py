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
from app.core.redis_cache import cache

router = APIRouter(prefix="/users", tags=["Users"])


# -------------------------
# USER: Profile
# -------------------------
@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        cache_key = f"user_profile_{user.id}"
        try:
            cached_profile = await cache.get(cache_key)
            if cached_profile:
                return cached_profile
        except Exception as e:
            print(f"Cache error: {e}")

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

        profile_data = {
            "id": user.id,
            "number": str(user.number) if user.number else "",
            "country_code": str(user.country_code) if user.country_code else "",
            "referral_code": str(user.referral_code) if user.referral_code else "",
            "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None,

            "wallet": {
                "balance": float(wallet.balance) if wallet and hasattr(wallet, 'balance') else 0.0,
                "income": float(wallet.income) if wallet and hasattr(wallet, 'income') else 0.0,
            },

            "levels": [
                {
                    "id": int(l.level_id) if hasattr(l, 'level_id') else 0,
                    "name": str(l.name) if hasattr(l, 'name') else "Unknown",
                    "daily_income": float(l.daily_income) if hasattr(l, 'daily_income') else 0.0,
                    "monthly_income": float(l.monthly_income) if hasattr(l, 'monthly_income') else 0.0,
                }
                for l in levels
            ] if levels else [],

            "total_tasks": int(total_tasks) if total_tasks is not None else 0,
            "completed_tasks": int(completed_tasks) if completed_tasks is not None else 0,
            "pending_tasks": int(pending_tasks) if pending_tasks is not None else 0,

            "total_referrals": int(total_referrals) if total_referrals is not None else 0,
            "active_referrals": int(active_referrals) if active_referrals is not None else 0,
            "referral_bonus": float(referral_bonus) if referral_bonus is not None else 0.0,

            "wealthfunds": [
                {
                    "id": int(wf.id) if hasattr(wf, 'id') else 0,
                    "name": str(wf.name) if hasattr(wf, 'name') else "Unknown",
                    "amount": float(wf.amount) if hasattr(wf, 'amount') else 0.0,
                    "total_profit": float(wf.total_profit) if hasattr(wf, 'total_profit') else 0.0,
                    "status": str(wf.status) if hasattr(wf, 'status') else "inactive",
                }
                for wf in wealthfunds
            ] if wealthfunds else [],
        }
        
        try:
            await cache.set(cache_key, profile_data, expire=300) # 5 mins cache
        except Exception as e:
            print(f"Cache set error: {e}")
            
        return profile_data
    except Exception as e:
        import traceback
        print(f"Profile error for user {user.id}: {str(e)}")
        print(traceback.format_exc())
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
