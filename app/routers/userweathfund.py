from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from typing import List
import logging

from app.core.redis_cache import cache as redis_cache
from app.database.database import get_async_db
from app.models.models import WealthFund, UserWealthFund, Wallet, User, Transaction, TransactionType
from app.routers.auth import get_current_user
from app.schema.schema import InvestWealthFundRequest, UserWealthFundResponse

logger = logging.getLogger("mmuAPI.wealthfund")

router = APIRouter(prefix="/user-wealthfunds", tags=["User Wealth Funds"])


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULED TASK: Update daily interest for all active, non-matured funds
# ─────────────────────────────────────────────────────────────────────────────
async def update_daily_interest(db: AsyncSession):
    """
    Accrues daily interest for active funds that haven't matured.
    Ensures interest is only added once per 24-hour period.
    """
    now = datetime.utcnow()
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.status == "active")
        .filter(UserWealthFund.end_date > now)
    )
    active_funds = result.scalars().all()

    updated_count = 0
    for fund in active_funds:
        # Check if 24 hours have passed since last update (or since start_date)
        last_update = fund.last_interest_update or fund.start_date
        if (now - last_update) >= timedelta(days=1):
            # Calculate daily interest (e.g., 2.5 means 2.5%)
            daily_gain = round((fund.daily_interest / 100.0) * fund.amount, 6)
            
            fund.today_interest = daily_gain
            fund.total_profit = round(fund.total_profit + daily_gain, 6)
            fund.last_interest_update = now
            updated_count += 1
            
            logger.info(f"Accrued KES {daily_gain} interest for fund {fund.id} (user {fund.user_id})")

    if updated_count > 0:
        await db.commit()
        logger.info(f"Daily interest update cycle complete. {updated_count} fund(s) updated.")


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULED TASK: Process matured wealth funds
# ─────────────────────────────────────────────────────────────────────────────
async def complete_matured_funds(db: AsyncSession):
    """
    Runs on a schedule.
    For each active fund whose end_date has passed:
      1. Calculate final payout = principal + total_profit
      2. Credit payout to wallet.income  (atomic within the same DB session)
      3. Record a WEALTH_FUND_MATURITY transaction for the income ledger
      4. Mark the fund as 'completed' and zero out today_interest
    Idempotency: we only select funds with status == 'active', so a fund
    that has already been completed will never be processed twice.
    """
    now = datetime.utcnow()
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.status == "active")
        .filter(UserWealthFund.end_date <= now)
    )
    matured_funds = result.scalars().all()

    processed = 0
    for fund in matured_funds:
        # ── 1. Fetch wallet ──────────────────────────────────────────────────
        wallet_result = await db.execute(
            select(Wallet).filter(Wallet.user_id == fund.user_id)
        )
        wallet = wallet_result.scalar_one_or_none()

        if not wallet:
            logger.warning(
                f"Wallet not found for user_id={fund.user_id} "
                f"(fund id={fund.id}). Skipping."
            )
            continue

        # ── 2. Calculate final payout ────────────────────────────────────────
        # Ensure total_profit reflects the full duration.
        # If the scheduler missed some days, recalculate from scratch.
        expected_total_profit = round(
            (fund.daily_interest / 100.0) * fund.amount * fund.duration_days, 6
        )
        # Use whichever is larger to avoid under-paying due to missed cycles.
        final_profit = max(fund.total_profit, expected_total_profit)
        final_payout = round(fund.amount + final_profit, 6)

        # ── 3. Credit wallet (income section) ───────────────────────────────
        wallet.income = round(wallet.income + final_payout, 6)
        db.add(wallet)

        # ── 4. Record income transaction ─────────────────────────────────────
        db.add(Transaction(
            user_id=fund.user_id,
            type=TransactionType.WEALTH_FUND_MATURITY.value,   # ← fixed enum
            amount=final_payout,
            created_at=now,
        ))

        # ── 5. Mark fund as completed ────────────────────────────────────────
        fund.status = "completed"
        fund.total_profit = final_profit
        fund.today_interest = 0.0
        db.add(fund)

        # ── 6. Invalidate profile cache so wallet balance refreshes immediately ──
        try:
            await redis_cache.delete(f"user_profile_{fund.user_id}")
        except Exception as cache_exc:
            logger.warning(f"Cache invalidation failed for user {fund.user_id}: {cache_exc}")

        processed += 1
        logger.info(
            f"Fund id={fund.id} matured for user_id={fund.user_id}. "
            f"Payout={final_payout} (principal={fund.amount}, profit={final_profit})."
        )

    if processed:
        await db.commit()
        logger.info(f"Maturity processing complete: {processed} fund(s) settled.")


# ─────────────────────────────────────────────────────────────────────────────
# USER: Invest in a WealthFund product
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/invest", response_model=UserWealthFundResponse)
async def invest_in_wealthfund(
    data: InvestWealthFundRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Deducts the investment amount from wallet.income and creates a UserWealthFund
    record with the correct start_date, end_date, and initial profit values.
    """
    # ── Validate WealthFund product ──────────────────────────────────────────
    result = await db.execute(
        select(WealthFund).filter(WealthFund.id == data.wealthfund_id)
    )
    wealthfund = result.scalar_one_or_none()
    if not wealthfund:
        raise HTTPException(status_code=404, detail="Wealth fund not found")

    # ── Validate wallet ──────────────────────────────────────────────────────
    wallet_result = await db.execute(
        select(Wallet).filter(Wallet.user_id == user.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found")

    # ── Validate minimum investment ──────────────────────────────────────────
    if data.amount < 200:
        raise HTTPException(
            status_code=400, detail="Minimum investment amount is KES 200"
        )

    # ── Check sufficient income balance ──────────────────────────────────────
    if wallet.income < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient income balance")

    # ── Deduct from wallet ───────────────────────────────────────────────────
    wallet.income = round(wallet.income - data.amount, 6)
    db.add(wallet)

    # ── Record investment transaction ────────────────────────────────────────
    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.WEALTH_FUND_INVESTMENT.value,
        amount=data.amount,
        created_at=datetime.utcnow(),
    ))

    # ── Calculate dates ──────────────────────────────────────────────────────
    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=wealthfund.duration_days)

    # ── Create UserWealthFund record ─────────────────────────────────────────
    user_wealthfund = UserWealthFund(
        user_id=user.id,
        wealthfund_id=wealthfund.id,
        image=wealthfund.image,
        name=wealthfund.name,
        amount=data.amount,
        profit_percent=wealthfund.profit_percent,
        duration_days=wealthfund.duration_days,
        daily_interest=wealthfund.daily_interest,
        total_profit=0.0,
        today_interest=0.0,
        start_date=start_date,
        end_date=end_date,
        status="active",
    )
    db.add(user_wealthfund)

    await db.commit()
    await db.refresh(user_wealthfund)

    logger.info(
        f"User {user.id} invested KES {data.amount} in WealthFund '{wealthfund.name}'. "
        f"Matures on {end_date.date()}."
    )
    return user_wealthfund


# ─────────────────────────────────────────────────────────────────────────────
# USER: Get my WealthFund investments
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_model=List[UserWealthFundResponse])
async def get_my_wealthfunds(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Returns all WealthFund investments for the authenticated user, newest first."""
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.user_id == user.id)
        .order_by(UserWealthFund.created_at.desc())
    )
    return result.scalars().all()
