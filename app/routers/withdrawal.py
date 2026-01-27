from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime

from passlib.context import CryptContext

from app.models.models import User, Withdrawal, Wallet, Transaction
from app.database.database import get_async_db
from app.routers.auth import get_current_user, get_current_admin
from app.schema.schema import (
    WithdrawalCreate,
    WithdrawalResponse,
    WithdrawalUpdateStatus,
)

router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])

# -------------------------
# CONFIG
# -------------------------
TAX_RATE = 0.10  # 10%

pwd_context_pin = CryptContext(schemes=["argon2"], deprecated="auto")
ARGON2_MAX_LENGTH = 128


def verify_pin(pin: str, hashed_pin: str) -> bool:
    return pwd_context_pin.verify(pin[:ARGON2_MAX_LENGTH], hashed_pin)


# -------------------------
# USER: Request Withdrawal
# -------------------------
@router.post("/", response_model=WithdrawalResponse)
async def request_withdrawal(
    withdrawal: WithdrawalCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if not current_user.withdrawal_pin:
        raise HTTPException(status_code=400, detail="Withdrawal PIN not set")

    if not verify_pin(withdrawal.pin, current_user.withdrawal_pin):
        raise HTTPException(status_code=400, detail="Invalid withdrawal PIN")

    result = await db.execute(
        select(Wallet).filter(Wallet.user_id == current_user.id)
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if wallet.income < withdrawal.amount:
        raise HTTPException(status_code=400, detail="Insufficient income balance")

    # --- TAX CALCULATION ---
    tax = round(withdrawal.amount * TAX_RATE, 2)
    net_amount = withdrawal.amount - tax

    # Deduct FULL amount
    wallet.income -= withdrawal.amount
    db.add(wallet)

    new_withdrawal = Withdrawal(
        user_id=current_user.id,
        name=withdrawal.name,
        number=withdrawal.number,
        amount=withdrawal.amount,
        tax=tax,
        net_amount=net_amount,
        status="pending",
        created_at=datetime.utcnow(),
    )
    db.add(new_withdrawal)

    # Ledger: withdrawal request
    db.add(
        Transaction(
            user_id=current_user.id,
            type="withdrawal_request",
            amount=withdrawal.amount,
            created_at=datetime.utcnow(),
        )
    )

    # Ledger: tax
    db.add(
        Transaction(
            user_id=current_user.id,
            type="withdrawal_tax",
            amount=tax,
            created_at=datetime.utcnow(),
        )
    )

    await db.commit()
    await db.refresh(new_withdrawal)
    return new_withdrawal


# -------------------------
# ADMIN: Get all withdrawals
# -------------------------
@router.get("/", response_model=List[WithdrawalResponse])
async def get_all_withdrawals(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Withdrawal))
    return result.scalars().all()


# -------------------------
# ADMIN: Approve / Reject
# -------------------------
@router.patch("/{withdrawal_id}/status", response_model=WithdrawalResponse)
async def update_withdrawal_status(
    withdrawal_id: int,
    status_update: WithdrawalUpdateStatus,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(Withdrawal).filter(Withdrawal.id == withdrawal_id)
    )
    withdrawal = result.scalar_one_or_none()

    if not withdrawal:
        raise HTTPException(status_code=404, detail="Withdrawal not found")

    if withdrawal.status != "pending":
        raise HTTPException(status_code=400, detail="Withdrawal already processed")

    withdrawal.status = status_update.status.lower()
    db.add(withdrawal)

    wallet_result = await db.execute(
        select(Wallet).filter(Wallet.user_id == withdrawal.user_id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    # REJECT → refund full amount
    if withdrawal.status == "rejected":
        wallet.income += withdrawal.amount
        db.add(wallet)

        db.add(
            Transaction(
                user_id=withdrawal.user_id,
                type="withdrawal_rejected_refund",
                amount=withdrawal.amount,
                created_at=datetime.utcnow(),
            )
        )

    # APPROVE → user receives net amount
    if withdrawal.status == "approved":
        db.add(
            Transaction(
                user_id=withdrawal.user_id,
                type="withdrawal_approved",
                amount=withdrawal.net_amount,
                created_at=datetime.utcnow(),
            )
        )

    await db.commit()
    await db.refresh(withdrawal)
    return withdrawal


# -------------------------
# USER: Get own withdrawals
# -------------------------
@router.get("/me", response_model=List[WithdrawalResponse])
async def get_my_withdrawals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(Withdrawal).filter(Withdrawal.user_id == current_user.id)
    )
    return result.scalars().all()
