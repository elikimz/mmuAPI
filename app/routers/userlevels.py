from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta

from app.database.database import get_async_db
from app.models.models import (
    Referral,
    User,
    UserLevel,
    Level,
    Wallet,
    Task,
    UserTask,
    UserTaskPending,
    UserTaskCompleted,
    Transaction,
    TransactionType,
)
from app.routers.auth import get_current_user
from app.schema.schema import BuyLevelRequest, UserLevelResponse, LevelInfoResponse
from app.core.websocket_manager import manager
from app.core.redis_cache import cache

router = APIRouter(prefix="/user-levels", tags=["User Levels"])

BONUS_PERCENTAGES = {"A": 0.09, "B": 0.03, "C": 0.01}


# -------------------------
# Helper: compute expires_at from level.expiry_days
# -------------------------
def compute_expires_at(expiry_days: int | None) -> datetime | None:
    """Return a UTC datetime when the level expires, or None if it never expires."""
    if expiry_days and expiry_days > 0:
        return datetime.utcnow() + timedelta(days=expiry_days)
    return None


# -------------------------
# Helper: apply referral bonus to wallet and record transaction
# -------------------------
async def apply_referral_bonus(db: AsyncSession, user_id: int, bonus_amount: float):
    wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        return  # Don't crash the whole purchase if a referrer's wallet is missing

    wallet.income += bonus_amount
    db.add(Transaction(
        user_id=user_id,
        type=TransactionType.REFERRAL_BONUS.value,
        amount=bonus_amount,
        created_at=datetime.utcnow()
    ))
    db.add(wallet)


# -------------------------
# Helper: clear all task records for a user and assign tasks for a given level
# This is the single source of truth for task assignment on level change.
# Must be called within an active transaction.
# -------------------------
async def reset_user_tasks_for_level(db: AsyncSession, user_id: int, level_id: int):
    """
    Atomically removes ALL existing task records for the user (active, pending,
    and completed) and assigns fresh tasks for the specified level.

    This guarantees that a user can never hold tasks from more than one level
    at any point in time.
    """
    # 1. Remove all pending tasks for the user
    await db.execute(
        delete(UserTaskPending).where(UserTaskPending.user_id == user_id)
    )

    # 2. Remove all completed tasks for the user
    await db.execute(
        delete(UserTaskCompleted).where(UserTaskCompleted.user_id == user_id)
    )

    # 3. Remove all active/assigned tasks for the user
    await db.execute(
        delete(UserTask).where(UserTask.user_id == user_id)
    )

    # 4. Assign all tasks belonging to the new level
    tasks_result = await db.execute(
        select(Task).filter(Task.level_id == level_id)
    )
    new_tasks = tasks_result.scalars().all()

    for t in new_tasks:
        db.add(UserTask(
            user_id=user_id,
            task_id=t.id,
            video_url=t.video_url,
            completed=False,
        ))

    return len(new_tasks)


# -------------------------
# USER: Get own levels
# -------------------------
@router.get("/me", response_model=List[UserLevelResponse])
async def get_my_levels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
    return result.scalars().all()


# -------------------------
# USER: Get all available levels (public)
# -------------------------
@router.get("/all", response_model=List[LevelInfoResponse])
async def get_all_levels(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Level).filter(Level.locked == False))
    return result.scalars().all()


# ============================================================
# BUY LEVEL
# ============================================================
@router.post("/buy", response_model=UserLevelResponse)
async def buy_level(
    request: BuyLevelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    level = (await db.execute(select(Level).filter(Level.id == request.level_id))).scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if level.locked:
        raise HTTPException(status_code=403, detail="This level is currently locked and cannot be purchased")

    wallet = (await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))).scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="User wallet not found")

    if (await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))).scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already own a level. Use the upgrade endpoint instead.")

    if wallet.balance < level.earnest_money:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Required: {level.earnest_money}, Available: {wallet.balance}"
        )

    try:
        now = datetime.utcnow()

        # Deduct purchase cost
        wallet.balance -= level.earnest_money
        db.add(Transaction(
            user_id=current_user.id,
            type=TransactionType.LEVEL_PURCHASE.value,
            amount=level.earnest_money,
            created_at=now
        ))

        # Compute expiry
        expires_at = compute_expires_at(level.expiry_days)

        # Create user level record
        user_level = UserLevel(
            user_id=current_user.id,
            level_id=level.id,
            name=level.name,
            description=level.description,
            earnest_money=level.earnest_money,
            workload=level.workload,
            salary=level.salary,
            daily_income=level.daily_income,
            monthly_income=level.monthly_income,
            annual_income=level.annual_income,
            created_at=now,
            expires_at=expires_at,
        )
        db.add(user_level)

        # Assign all tasks for this level to the user via the shared helper.
        # This ensures buy and upgrade share the same task-assignment logic.
        assigned_count = await reset_user_tasks_for_level(db, current_user.id, level.id)

        db.add(wallet)

        # =========================
        # REFERRAL BONUS (paid levels only)
        # =========================
        if level.earnest_money > 0:
            referrals = (await db.execute(
                select(Referral).where(Referral.referred_id == current_user.id)
            )).scalars().all()

            for ref in referrals:
                referrer_level = (await db.execute(
                    select(UserLevel).where(UserLevel.user_id == ref.referrer_id)
                )).scalar_one_or_none()
                if not referrer_level:
                    continue

                bonus_base = min(referrer_level.earnest_money, level.earnest_money)
                if bonus_base <= 0:
                    continue

                bonus_amount = round(bonus_base * BONUS_PERCENTAGES.get(ref.level, 0), 2)
                await apply_referral_bonus(db, ref.referrer_id, bonus_amount)
                ref.is_active = True
                ref.bonus_amount = bonus_amount
                db.add(ref)

        await db.commit()
        await db.refresh(user_level)
        print(
            f"User {current_user.id} purchased level '{level.name}' "
            f"({assigned_count} tasks assigned, expires_at={expires_at})."
        )

        try:
            await cache.delete(f"user_profile_{current_user.id}")
            await manager.send_personal_message(current_user.id, {
                "type": "LEVEL_PURCHASED",
                "level_id": level.id,
                "level_name": level.name,
                "new_balance": wallet.balance,
                "expires_at": expires_at.isoformat() if expires_at else None,
            })
        except Exception as comm_e:
            print(f"Warning: Post-commit communication failed for user {current_user.id}: {comm_e}")

        return user_level

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        print(f"Error purchasing level for user {current_user.id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during purchase: {str(e)}")


# ============================================================
# UPGRADE LEVEL
# ============================================================
@router.post("/upgrade", response_model=UserLevelResponse)
async def upgrade_level(
    request: BuyLevelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    level = (await db.execute(select(Level).filter(Level.id == request.level_id))).scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")
    if level.locked:
        raise HTTPException(status_code=403, detail="This level is currently locked")

    wallet = (await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))).scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="User wallet not found")

    current_level = (await db.execute(
        select(UserLevel).filter(UserLevel.user_id == current_user.id)
    )).scalar_one_or_none()
    if not current_level:
        raise HTTPException(status_code=400, detail="You do not have a level to upgrade from")

    if level.earnest_money <= current_level.earnest_money:
        raise HTTPException(status_code=400, detail="You must upgrade to a higher-tier level")

    difference = level.earnest_money - current_level.earnest_money
    if wallet.balance < difference:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Required: {difference}, Available: {wallet.balance}"
        )

    try:
        old_level_id = current_level.level_id
        old_level_name = current_level.name
        old_level_price = current_level.earnest_money
        now = datetime.utcnow()

        wallet.balance -= difference
        wallet.income += old_level_price
        db.add(Transaction(
            user_id=current_user.id,
            type=TransactionType.LEVEL_UPGRADE.value,
            amount=difference,
            created_at=now
        ))

        # Compute new expiry
        expires_at = compute_expires_at(level.expiry_days)

        # Update the user's level record in-place
        current_level.level_id = level.id
        current_level.name = level.name
        current_level.description = level.description
        current_level.earnest_money = level.earnest_money
        current_level.workload = level.workload
        current_level.salary = level.salary
        current_level.daily_income = level.daily_income
        current_level.monthly_income = level.monthly_income
        current_level.annual_income = level.annual_income
        current_level.created_at = now
        current_level.expires_at = expires_at
        db.add(current_level)

        # ---------------------------------------------------------------
        # FIX: Clear all tasks from the previous level and assign tasks
        # for the new level within the same transaction.
        #
        # This guarantees:
        #   1. No stale tasks from old_level_id remain in any task table.
        #   2. All tasks for the new level.id are freshly assigned.
        #   3. The operation is atomic — either all changes commit or none do.
        # ---------------------------------------------------------------
        assigned_count = await reset_user_tasks_for_level(db, current_user.id, level.id)

        db.add(wallet)

        # =========================
        # REFERRAL BONUS ON FIRST PAID UPGRADE
        # =========================
        if old_level_price == 0 and level.earnest_money > 0:
            referrals = (await db.execute(
                select(Referral).where(Referral.referred_id == current_user.id)
            )).scalars().all()

            for ref in referrals:
                referrer_level = (await db.execute(
                    select(UserLevel).where(UserLevel.user_id == ref.referrer_id)
                )).scalar_one_or_none()
                if not referrer_level:
                    continue

                bonus_base = min(referrer_level.earnest_money, level.earnest_money)
                if bonus_base <= 0:
                    continue

                bonus_amount = round(bonus_base * BONUS_PERCENTAGES.get(ref.level, 0), 2)
                await apply_referral_bonus(db, ref.referrer_id, bonus_amount)
                ref.is_active = True
                ref.bonus_amount = bonus_amount
                db.add(ref)

        await db.commit()
        await db.refresh(current_level)
        print(
            f"User {current_user.id} upgraded from level '{old_level_name}' (id={old_level_id}) "
            f"to '{level.name}' (id={level.id}). "
            f"Old tasks purged, {assigned_count} new tasks assigned. "
            f"expires_at={expires_at}."
        )

        try:
            await cache.delete(f"user_profile_{current_user.id}")
            await manager.send_personal_message(current_user.id, {
                "type": "LEVEL_UPGRADED",
                "level_id": level.id,
                "level_name": level.name,
                "new_balance": wallet.balance,
                "expires_at": expires_at.isoformat() if expires_at else None,
            })
        except Exception as comm_e:
            print(f"Warning: Post-commit communication failed for user {current_user.id}: {comm_e}")

        return current_level

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        import traceback
        print(f"Error upgrading level for user {current_user.id}: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during upgrade: {str(e)}")
