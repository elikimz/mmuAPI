


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

#     # All positive earnings types
#     earning_types = [
#         TransactionType.TASK_REWARD,
#         TransactionType.REFERRAL_BONUS,
#         TransactionType.REFERRAL_REBATE,  # ✅ include rebate
#         TransactionType.WEALTH_FUND_MATURITY,
#         TransactionType.COMMISSION,
#         TransactionType.GIFT_REDEMPTION,
#     ]

#     async def sum_earnings(start_date: datetime = None, types: list = None):
#         types = types or earning_types
#         query = select(func.coalesce(func.sum(Transaction.amount), 0)).filter(
#             Transaction.user_id == current_user.id,
#             Transaction.type.in_(types),
#             Transaction.amount > 0
#         )
#         if start_date:
#             query = query.filter(Transaction.created_at >= start_date)
#         result = await db.execute(query)
#         return result.scalar_one_or_none() or 0

#     # Totals including all earnings types
#     today_earnings = await sum_earnings(start_date=today_start)
#     week_earnings = await sum_earnings(start_date=week_start)
#     month_earnings = await sum_earnings(start_date=month_start)

#     # Breakdown by type
#     total_commission = today_earnings  # ✅ now total earnings instead of only commissions
#     referral_bonus = await sum_earnings(types=[TransactionType.REFERRAL_BONUS])
#     referral_rebate = await sum_earnings(types=[TransactionType.GIFT_REDEMPTION])
#     gift_earnings = await sum_earnings(types=[TransactionType.GIFT_REDEMPTION])

#     return {
#         "today_earnings": round(today_earnings, 2),
#         "week_earnings": round(week_earnings, 2),
#         "month_earnings": round(month_earnings, 2),
#         "total_commission": round(today_earnings, 2),  # ✅ now includes all earnings
#         "referral_bonus": round(referral_bonus, 2),
#         "referral_rebate": round(referral_rebate, 2),
#         "gift_earnings": round(gift_earnings, 2),
#     }



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

    # All positive earnings types
    earning_types = [
        TransactionType.TASK_REWARD,
        TransactionType.REFERRAL_BONUS,
        TransactionType.REFERRAL_REBATE,
        TransactionType.WEALTH_FUND_MATURITY,
        TransactionType.COMMISSION,
        TransactionType.GIFT_REDEMPTION,
    ]

    async def sum_earnings(start_date: datetime = None, types: list = None):
        types = types or earning_types
        query = select(func.coalesce(func.sum(Transaction.amount), 0)).filter(
            Transaction.user_id == current_user.id,
            Transaction.type.in_(types),
            Transaction.amount > 0
        )
        if start_date:
            query = query.filter(Transaction.created_at >= start_date)
        result = await db.execute(query)
        return result.scalar_one_or_none() or 0

    # Totals including all earnings types
    today_earnings = await sum_earnings(start_date=today_start)
    week_earnings = await sum_earnings(start_date=week_start)
    month_earnings = await sum_earnings(start_date=month_start)

    # Breakdown by type
    referral_bonus = await sum_earnings(types=[TransactionType.REFERRAL_BONUS])
    referral_rebate = await sum_earnings(types=[TransactionType.REFERRAL_REBATE])
    gift_earnings = await sum_earnings(types=[TransactionType.GIFT_REDEMPTION])

    # Calculate total_commission as the sum of all specified transaction types
    total_commission = await sum_earnings()

    return {
        "today_earnings": round(today_earnings, 2),
        "week_earnings": round(week_earnings, 2),
        "month_earnings": round(month_earnings, 2),
        "total_commission": round(total_commission, 2),
        "referral_bonus": round(referral_bonus, 2),
        "referral_rebate": round(referral_rebate, 2),
        "gift_earnings": round(gift_earnings, 2),
    }
