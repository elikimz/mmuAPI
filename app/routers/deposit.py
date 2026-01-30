from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import User, Deposit, Wallet, Transaction
from app.database.database import get_async_db
from app.routers.auth import get_current_admin, get_current_user
from app.schema.schema import DepositCreate, DepositResponse, DepositUpdateStatus
from typing import List

from datetime import datetime

router = APIRouter(prefix="/deposits", tags=["Deposits"])

# -------------------------
# USER: Create a deposit
# -------------------------
@router.post("/", response_model=DepositResponse)
async def create_deposit(
    deposit: DepositCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    new_deposit = Deposit(
        user_id=current_user.id,
        name=deposit.name,
        number=deposit.number,
        account_number=deposit.account_number,
        payment_method=deposit.payment_method,
        message=deposit.message,
        amount=deposit.amount,
        status="pending",
        created_at=datetime.utcnow(),
    )

    db.add(new_deposit)
    await db.commit()
    await db.refresh(new_deposit)
    return new_deposit


# -------------------------
# ADMIN: Get all deposits
# -------------------------
@router.get("/", response_model=List[DepositResponse])
async def get_all_deposits(admin: User = Depends(get_current_admin), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Deposit))
    deposits = result.scalars().all()
    return deposits


# -------------------------
# ADMIN: Approve or Cancel Deposit
# -------------------------
@router.patch("/{deposit_id}/status", response_model=DepositResponse)
async def update_deposit_status(
    deposit_id: int,
    status_update: DepositUpdateStatus,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    # Find deposit
    result = await db.execute(select(Deposit).filter(Deposit.id == deposit_id))
    deposit = result.scalar_one_or_none()
    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    # Update status
    deposit.status = status_update.status
    db.add(deposit)

    # If approved, add amount to user's wallet & create transaction
    if status_update.status.lower() == "approved":
        # Load wallet
        wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == deposit.user_id))
        wallet = wallet_result.scalar_one_or_none()
        if wallet is None:
            raise HTTPException(status_code=404, detail="User wallet not found")

        wallet.balance += deposit.amount
        db.add(wallet)

        # Record transaction
        transaction = Transaction(
            user_id=deposit.user_id,
            type="deposit",
            amount=deposit.amount,
            created_at=datetime.utcnow(),
        )
        db.add(transaction)

    await db.commit()
    await db.refresh(deposit)
    return deposit


# -------------------------
# USER: Get own deposits
# -------------------------
# @router.get("/me", response_model=List[DepositResponse])
# async def get_my_deposits(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(select(Deposit).filter(Deposit.user_id == current_user.id))
#     deposits = result.scalars().all()
#     return deposits




@router.get("/me")
async def get_my_deposits(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Get deposits
    deposits_result = await db.execute(
        select(Deposit).where(Deposit.user_id == current_user.id)
    )
    deposits = deposits_result.scalars().all()

    # Get wallet
    wallet_result = await db.execute(
        select(Wallet).where(Wallet.user_id == current_user.id)
    )
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    return {
        "wallet_balance": wallet.balance,
        "wallet_income": wallet.income,
        "deposits": deposits,
    }
