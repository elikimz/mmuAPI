# # from fastapi import APIRouter, Depends, HTTPException
# # from sqlalchemy.ext.asyncio import AsyncSession
# # from sqlalchemy.future import select
# # from sqlalchemy import func
# # from datetime import datetime, timedelta
# # from typing import Dict

# # from app.database.database import get_async_db
# # from app.models.models import User, Transaction, Wallet
# # from app.routers.auth import get_current_user

# # router = APIRouter(prefix="/earnings", tags=["Earnings"])

# # @router.get("/overview", response_model=Dict[str, float])
# # async def get_earnings_overview(
# #     current_user: User = Depends(get_current_user),
# #     db: AsyncSession = Depends(get_async_db),
# # ):
# #     # Get wallet
# #     wallet_result = await db.execute(
# #         select(Wallet).filter(Wallet.user_id == current_user.id)
# #     )
# #     wallet = wallet_result.scalar_one_or_none()
# #     if not wallet:
# #         raise HTTPException(status_code=404, detail="Wallet not found")

# #     # Calculate time ranges
# #     today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
# #     week_start = today_start - timedelta(days=today_start.weekday())
# #     month_start = today_start.replace(day=1)

# #     # Today's earnings (sum of all positive transactions today)
# #     today_result = await db.execute(
# #         select(func.coalesce(func.sum(Transaction.amount), 0))
# #         .filter(
# #             Transaction.user_id == current_user.id,
# #             Transaction.type.not_like("withdrawal%"),
# #             Transaction.created_at >= today_start,
# #             Transaction.amount > 0,
# #         )
# #     )
# #     today_earnings = today_result.scalar_one_or_none() or 0

# #     # This week's earnings
# #     week_result = await db.execute(
# #         select(func.coalesce(func.sum(Transaction.amount), 0))
# #         .filter(
# #             Transaction.user_id == current_user.id,
# #             Transaction.type.not_like("withdrawal%"),
# #             Transaction.created_at >= week_start,
# #             Transaction.amount > 0,
# #         )
# #     )
# #     week_earnings = week_result.scalar_one_or_none() or 0

# #     # This month's earnings
# #     month_result = await db.execute(
# #         select(func.coalesce(func.sum(Transaction.amount), 0))
# #         .filter(
# #             Transaction.user_id == current_user.id,
# #             Transaction.type.not_like("withdrawal%"),
# #             Transaction.created_at >= month_start,
# #             Transaction.amount > 0,
# #         )
# #     )
# #     month_earnings = month_result.scalar_one_or_none() or 0

# #     # Total commission (e.g., from tasks, referrals, etc.)
# #     commission_result = await db.execute(
# #         select(func.coalesce(func.sum(Transaction.amount), 0))
# #         .filter(
# #             Transaction.user_id == current_user.id,
# #             Transaction.type.like("%commission%"),
# #             Transaction.amount > 0,
# #         )
# #     )
# #     total_commission = commission_result.scalar_one_or_none() or 0

# #     # Referral bonus
# #     referral_result = await db.execute(
# #         select(func.coalesce(func.sum(Transaction.amount), 0))
# #         .filter(
# #             Transaction.user_id == current_user.id,
# #             Transaction.type.like("%referral%"),
# #             Transaction.amount > 0,
# #         )
# #     )
# #     referral_bonus = referral_result.scalar_one_or_none() or 0

# #     return {
# #         "today_earnings": today_earnings,
# #         "week_earnings": week_earnings,
# #         "month_earnings": month_earnings,
# #         "total_commission": total_commission,
# #         "referral_bonus": referral_bonus,
# #     }






# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy import func
# from datetime import datetime, timedelta
# from typing import Dict

# from app.database.database import get_async_db
# from app.models.models import User, Transaction, Wallet
# from app.routers.auth import get_current_user

# router = APIRouter(prefix="/earnings", tags=["Earnings"])


# @router.get("/overview", response_model=Dict[str, float])
# async def get_earnings_overview(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     # Fetch wallet
#     wallet_result = await db.execute(
#         select(Wallet).filter(Wallet.user_id == current_user.id)
#     )
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="Wallet not found")

#     now = datetime.utcnow()
#     today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
#     week_start = today_start - timedelta(days=today_start.weekday())  # Monday
#     month_start = today_start.replace(day=1)

#     # Helper to sum positive transactions filtered by type and date
#     async def sum_transactions(start_date: datetime = None, types_like: str = None, types_not_like: str = None):
#         query = select(func.coalesce(func.sum(Transaction.amount), 0)).filter(
#             Transaction.user_id == current_user.id,
#             Transaction.amount > 0
#         )
#         if start_date:
#             query = query.filter(Transaction.created_at >= start_date)
#         if types_like:
#             query = query.filter(Transaction.type.like(types_like))
#         if types_not_like:
#             query = query.filter(Transaction.type.not_like(types_not_like))
#         result = await db.execute(query)
#         return result.scalar_one_or_none() or 0

#     # Earnings (exclude withdrawals)
#     today_earnings = await sum_transactions(today_start, types_not_like="withdrawal%")
#     week_earnings = await sum_transactions(week_start, types_not_like="withdrawal%")
#     month_earnings = await sum_transactions(month_start, types_not_like="withdrawal%")

#     # Commissions (specific)
#     total_commission = await sum_transactions(types_like="%commission%")

#     # Referral bonuses
#     referral_bonus = await sum_transactions(types_like="%referral%")

#     return {
#         "today_earnings": round(today_earnings, 2),
#         "week_earnings": round(week_earnings, 2),
#         "month_earnings": round(month_earnings, 2),
#         "total_commission": round(total_commission, 2),
#         "referral_bonus": round(referral_bonus, 2),
#     }



from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict

from app.database.database import get_async_db
from app.models.models import User, Transaction, Wallet, TransactionType
from app.routers.auth import get_current_user

router = APIRouter(prefix="/earnings", tags=["Earnings"])


@router.get("/overview", response_model=Dict[str, float])
async def get_earnings_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Fetch wallet
    wallet_result = await db.execute(
        select(Wallet).filter(Wallet.user_id == current_user.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())  # Monday
    month_start = today_start.replace(day=1)

    # Only positive earnings types
    earning_types = [
        TransactionType.TASK_REWARD,
        TransactionType.REFERRAL_BONUS,
        TransactionType.WEALTH_FUND_MATURITY,
        TransactionType.COMMISSION,
    ]

    async def sum_earnings(start_date: datetime = None):
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type.in_(earning_types),
            Transaction.amount > 0
        )
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        result = await db.execute(query)
        return result.scalar_one_or_none() or 0

    today_earnings = await sum_earnings(today_start)
    week_earnings = await sum_earnings(week_start)
    month_earnings = await sum_earnings(month_start)

    # Total commission specifically
    commission_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == TransactionType.COMMISSION,
            Transaction.amount > 0
        )
    )
    total_commission = commission_result.scalar_one_or_none() or 0

    # Total referral bonuses
    referral_result = await db.execute(
        select(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type == TransactionType.REFERRAL_BONUS,
            Transaction.amount > 0
        )
    )
    referral_bonus = referral_result.scalar_one_or_none() or 0

    return {
        "today_earnings": round(today_earnings, 2),
        "week_earnings": round(week_earnings, 2),
        "month_earnings": round(month_earnings, 2),
        "total_commission": round(total_commission, 2),
        "referral_bonus": round(referral_bonus, 2),
    }
