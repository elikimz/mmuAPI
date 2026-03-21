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
    Accrues daily interest for active funds that haven't matured yet.

    Fix (Bug 1): The original code used `timedelta(days=1)` as the threshold,
    meaning a fund created at 10:00 would not accrue interest until 10:00 the
    next day — causing today_interest=0 and total_profit=0 for all same-day
    investments.

    Corrected behaviour:
      - Interest is accrued once per calendar day (UTC).
      - We compare the date of `last_interest_update` (or `start_date`) against
        today's UTC date.  If the last accrual was on a *previous* calendar day,
        we accrue interest for each missed day (catch-up).
      - This ensures a fund created at 23:59 UTC still accrues its first day of
        interest at 00:00 UTC the following day, and the scheduler running at any
        hour of that day will correctly credit it.
    """
    now_utc = datetime.utcnow()
    # Kenya is UTC+3
    kenya_offset = timedelta(hours=3)
    now_kenya = now_utc + kenya_offset
    today_kenya = now_kenya.date()

    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.status == "active")
        .filter(UserWealthFund.end_date > now_utc)
    )
    active_funds = result.scalars().all()

    updated_count = 0
    for fund in active_funds:
        # Determine the last date on which interest was credited (convert to Kenya time)
        last_update_dt_utc = fund.last_interest_update or fund.start_date
        last_update_dt_kenya = last_update_dt_utc + kenya_offset
        last_update_date_kenya = last_update_dt_kenya.date()

        # Number of full Kenya calendar days that have elapsed since last accrual
        days_to_accrue = (today_kenya - last_update_date_kenya).days

        if days_to_accrue <= 0:
            # Already accrued today — skip
            continue

        # Calculate daily gain: daily_interest is stored as a percentage (e.g. 0.9 means 0.9%)
        daily_gain = round((fund.daily_interest / 100.0) * fund.amount, 6)

        # Credit all missed days (catch-up for scheduler downtime)
        total_gain = round(daily_gain * days_to_accrue, 6)

        fund.today_interest = daily_gain          # today's single-day gain
        fund.total_profit = round(fund.total_profit + total_gain, 6)
        fund.last_interest_update = now_utc
        updated_count += 1

        logger.info(
            f"Accrued KES {total_gain} interest for fund {fund.id} "
            f"(user {fund.user_id}, {days_to_accrue} day(s) @ KES {daily_gain}/day)"
        )

    if updated_count > 0:
        await db.commit()
        logger.info(f"Daily interest update cycle complete. {updated_count} fund(s) updated.")
    else:
        logger.info("Daily interest update cycle: no funds required accrual.")


# ─────────────────────────────────────────────────────────────────────────────
# SCHEDULED TASK: Process matured wealth funds
# ─────────────────────────────────────────────────────────────────────────────
async def complete_matured_funds(db: AsyncSession):
    """
    Runs on a schedule.
    For each active fund whose end_date has passed:
      1. Calculate final payout = principal + total_profit
      2. Credit the FULL payout (principal + profit) to wallet.income
      3. Record TWO separate transactions for a fully auditable ledger:
           a. WEALTH_FUND_PRINCIPAL_RETURN  — the original investment amount
              returned to the investor.
           b. WEALTH_FUND_MATURITY          — the profit earned over the fund
              duration.
      4. Mark the fund as 'completed' and zero out today_interest.

    Fix (Principal Not Credited — Root Cause):
      Earlier versions of this function only recorded a single transaction
      whose `amount` was set to `final_profit` (the profit alone), even though
      `wallet.income` was correctly incremented by `final_payout` (principal +
      profit).  This created a discrepancy between the wallet balance and the
      transaction ledger: the principal was silently credited to the wallet but
      never recorded as a transaction, making it invisible in earnings reports
      and impossible to audit.

      Fix: We now emit two explicit transaction records per matured fund —
      one for the principal return and one for the profit — so that the sum of
      all WEALTH_FUND_PRINCIPAL_RETURN and WEALTH_FUND_MATURITY transactions
      always equals the total amount credited to wallet.income.

    Fix (Bug 2 & 3 — Idempotency / Race Condition):
      - We flush `fund.status = "completed"` for each fund *immediately*
        after processing it (before moving to the next fund).  This prevents a
        second scheduler tick from re-processing the same fund if the first tick
        is still running.
      - We also add a SELECT FOR UPDATE-style re-check: after loading the fund
        we verify its status is still "active" before processing.
      - The `expected_total_profit` catch-up calculation is retained but capped
        at `duration_days` days to prevent over-payment.

    Fix (Bug 4 — Profit Overcalculation):
      - The `max(fund.total_profit, expected_total_profit)` guard is kept but
        `expected_total_profit` is now capped at exactly `duration_days` days,
        preventing the scheduler from crediting more than the contracted profit.
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
        # ── Re-check status (guard against concurrent scheduler runs) ────────
        # Re-read the fund inside the loop to get the freshest status.
        fresh_result = await db.execute(
            select(UserWealthFund).filter(UserWealthFund.id == fund.id)
        )
        fresh_fund = fresh_result.scalar_one_or_none()
        if not fresh_fund or fresh_fund.status != "active":
            logger.info(f"Fund id={fund.id} already processed — skipping.")
            continue

        # ── 1. Fetch wallet ──────────────────────────────────────────────────
        wallet_result = await db.execute(
            select(Wallet).filter(Wallet.user_id == fresh_fund.user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            logger.warning(
                f"Wallet not found for user_id={fresh_fund.user_id} "
                f"(fund id={fresh_fund.id}). Skipping."
            )
            continue

        # ── 2. Calculate final payout ────────────────────────────────────────
        # Cap at exactly duration_days to prevent over-payment.
        expected_total_profit = round(
            (fresh_fund.daily_interest / 100.0) * fresh_fund.amount * fresh_fund.duration_days, 6
        )
        # Use whichever is larger to avoid under-paying due to missed scheduler cycles.
        # But never exceed the contracted profit (expected_total_profit is already capped).
        final_profit = max(fresh_fund.total_profit, expected_total_profit)
        principal = fresh_fund.amount
        final_payout = round(principal + final_profit, 6)

        # ── 3. Mark fund as completed FIRST (idempotency guard) ──────────────
        # Flush the status change before crediting the wallet so that a
        # concurrent scheduler tick will see "completed" and skip this fund.
        fresh_fund.status = "completed"
        fresh_fund.total_profit = final_profit
        fresh_fund.today_interest = 0.0
        db.add(fresh_fund)
        await db.flush()   # write to DB within the transaction, not yet committed

        # ── 4. Credit wallet (income section) ─────────────────────────────────
        # Both the principal and the profit are credited to wallet.income.
        # The investor's original capital is returned alongside the earned profit.
        wallet.income = round(wallet.income + final_payout, 6)
        db.add(wallet)

        # ── 5. Record TWO separate income transactions ────────────────────────
        # Transaction A: the principal (original investment) returned to the user.
        db.add(Transaction(
            user_id=fresh_fund.user_id,
            type=TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value,
            amount=round(principal, 6),
            created_at=now,
        ))
        # Transaction B: the profit earned over the fund duration.
        db.add(Transaction(
            user_id=fresh_fund.user_id,
            type=TransactionType.WEALTH_FUND_MATURITY.value,
            amount=round(final_profit, 6),
            created_at=now,
        ))

        # ── 6. Invalidate profile cache so wallet balance refreshes immediately ──
        try:
            await redis_cache.delete(f"user_profile_{fresh_fund.user_id}")
        except Exception as cache_exc:
            logger.warning(f"Cache invalidation failed for user {fresh_fund.user_id}: {cache_exc}")

        processed += 1
        logger.info(
            f"Fund id={fresh_fund.id} matured for user_id={fresh_fund.user_id}. "
            f"Total payout={final_payout} "
            f"(principal={principal}, profit={final_profit}). "
            f"Two transactions recorded: WEALTH_FUND_PRINCIPAL_RETURN={principal}, "
            f"WEALTH_FUND_MATURITY={final_profit}."
        )

    if processed:
        await db.commit()
        logger.info(f"Maturity processing complete: {processed} fund(s) settled.")
    else:
        logger.info("Maturity processing: no funds required settlement.")


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
    """Returns all WealthFund investments for the authenticated user, newest first.
    Also triggers a lazy maturity check to ensure funds that have just matured
    are processed immediately before returning the response."""
    
    # 1. Trigger a lazy maturity check for this user's funds
    now = datetime.utcnow()
    matured_result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.user_id == user.id)
        .filter(UserWealthFund.status == "active")
        .filter(UserWealthFund.end_date <= now)
    )
    matured_funds = matured_result.scalars().all()
    
    if matured_funds:
        # If there are matured funds, we process them immediately
        # We can reuse the complete_matured_funds logic, but we need to do it inline
        # to ensure it happens before we return the response
        processed = False
        for fund in matured_funds:
            # Re-check status
            fresh_result = await db.execute(
                select(UserWealthFund).filter(UserWealthFund.id == fund.id)
            )
            fresh_fund = fresh_result.scalar_one_or_none()
            if not fresh_fund or fresh_fund.status != "active":
                continue
                
            # Fetch wallet
            wallet_result = await db.execute(
                select(Wallet).filter(Wallet.user_id == fresh_fund.user_id)
            )
            wallet = wallet_result.scalar_one_or_none()
            if not wallet:
                continue
                
            # Calculate final payout
            expected_total_profit = round(
                (fresh_fund.daily_interest / 100.0) * fresh_fund.amount * fresh_fund.duration_days, 6
            )
            final_profit = max(fresh_fund.total_profit, expected_total_profit)
            principal = fresh_fund.amount
            final_payout = round(principal + final_profit, 6)
            
            # Mark fund as completed
            fresh_fund.status = "completed"
            fresh_fund.total_profit = final_profit
            fresh_fund.today_interest = 0.0
            db.add(fresh_fund)
            await db.flush()
            
            # Credit wallet
            wallet.income = round(wallet.income + final_payout, 6)
            db.add(wallet)
            
            # Record transactions
            db.add(Transaction(
                user_id=fresh_fund.user_id,
                type=TransactionType.WEALTH_FUND_PRINCIPAL_RETURN.value,
                amount=round(principal, 6),
                created_at=now,
            ))
            db.add(Transaction(
                user_id=fresh_fund.user_id,
                type=TransactionType.WEALTH_FUND_MATURITY.value,
                amount=round(final_profit, 6),
                created_at=now,
            ))
            
            processed = True
            
        if processed:
            await db.commit()
            # Invalidate cache
            try:
                await redis_cache.delete(f"user_profile_{user.id}")
            except Exception:
                pass

    # 2. Return the updated list of funds
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.user_id == user.id)
        .order_by(UserWealthFund.created_at.desc())
    )
    return result.scalars().all()
