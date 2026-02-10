


# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from typing import List
# from datetime import datetime

# from passlib.context import CryptContext

# from app.models.models import User, Withdrawal, Wallet, Transaction
# from app.database.database import get_async_db
# from app.routers.auth import get_current_user, get_current_admin
# from app.schema.schema import (
#     WithdrawalCreate,
#     WithdrawalResponse,
#     WithdrawalUpdateStatus,
# )

# router = APIRouter(prefix="/withdrawals", tags=["Withdrawals"])


# from datetime import datetime, time, timedelta, timezone

# KENYA_TZ = timezone(timedelta(hours=3))  # UTC+3



# # -------------------------
# # CONFIG
# # -------------------------
# TAX_RATE = 0.10  # 10%
# pwd_context_pin = CryptContext(schemes=["argon2"], deprecated="auto")
# ARGON2_MAX_LENGTH = 128

# def verify_pin(pin: str, hashed_pin: str) -> bool:
#     return pwd_context_pin.verify(pin[:ARGON2_MAX_LENGTH], hashed_pin)





# # # -------------------------
# # # USER: Request Withdrawal
# # # -------------------------
# # @router.post("/", response_model=WithdrawalResponse)
# # async def request_withdrawal(
# #     withdrawal: WithdrawalCreate,
# #     current_user: User = Depends(get_current_user),
# #     db: AsyncSession = Depends(get_async_db),
# # ):
# #     if not current_user.withdrawal_pin:
# #         raise HTTPException(status_code=400, detail="Withdrawal PIN not set")

# #     if not verify_pin(withdrawal.pin, current_user.withdrawal_pin):
# #         raise HTTPException(status_code=400, detail="Invalid withdrawal PIN")

# #     # Check existing pending withdrawals
# #     pending_result = await db.execute(
# #         select(Withdrawal).filter(
# #             Withdrawal.user_id == current_user.id,
# #             Withdrawal.status == "pending"
# #         )
# #     )
# #     existing_pending = pending_result.scalar_one_or_none()
# #     if existing_pending:
# #         raise HTTPException(
# #             status_code=400,
# #             detail="You already have a pending withdrawal. Please wait until it is processed."
# #         )

# #     wallet_result = await db.execute(
# #         select(Wallet).filter(Wallet.user_id == current_user.id)
# #     )
# #     wallet = wallet_result.scalar_one_or_none()
# #     if not wallet:
# #         raise HTTPException(status_code=404, detail="Wallet not found")

# #     if wallet.income < withdrawal.amount:
# #         raise HTTPException(status_code=400, detail="Insufficient income balance")

# #     # Tax calculation
# #     tax = round(withdrawal.amount * TAX_RATE, 2)
# #     net_amount = withdrawal.amount - tax

# #     # Deduct full amount
# #     wallet.income -= withdrawal.amount
# #     db.add(wallet)

# #     new_withdrawal = Withdrawal(
# #         user_id=current_user.id,
# #         name=withdrawal.name,
# #         number=withdrawal.number,
# #         amount=withdrawal.amount,
# #         tax=tax,
# #         net_amount=net_amount,
# #         status="pending",
# #         created_at=datetime.utcnow(),
# #     )
# #     db.add(new_withdrawal)

# #     # Ledger: withdrawal request
# #     db.add(
# #         Transaction(
# #             user_id=current_user.id,
# #             type="withdrawal_request",
# #             amount=withdrawal.amount,
# #             created_at=datetime.utcnow(),
# #         )
# #     )

# #     # Ledger: tax
# #     db.add(
# #         Transaction(
# #             user_id=current_user.id,
# #             type="withdrawal_tax",
# #             amount=tax,
# #             created_at=datetime.utcnow(),
# #         )
# #     )

# #     await db.commit()
# #     await db.refresh(new_withdrawal)
# #     return new_withdrawal





# @router.post("/", response_model=WithdrawalResponse)
# async def request_withdrawal(
#     withdrawal: WithdrawalCreate,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     if not current_user.withdrawal_pin:
#         raise HTTPException(status_code=400, detail="Withdrawal PIN not set")

#     if not verify_pin(withdrawal.pin, current_user.withdrawal_pin):
#         raise HTTPException(status_code=400, detail="Invalid withdrawal PIN")

#     # Kenya time now
#     now = datetime.now(KENYA_TZ)
#     weekday = now.weekday()  # Monday=0, Sunday=6
#     if weekday == 6:  # Sunday
#         raise HTTPException(status_code=400, detail="Withdrawals not allowed on Sunday")
    
#     if not (time(9, 0) <= now.time() <= time(18, 0)):
#         raise HTTPException(status_code=400, detail="Withdrawals allowed only from 9AM to 6PM Kenya time")

#     # Check existing pending withdrawals
#     pending_result = await db.execute(
#         select(Withdrawal).filter(
#             Withdrawal.user_id == current_user.id,
#             Withdrawal.status == "pending"
#         )
#     )
#     existing_pending = pending_result.scalar_one_or_none()
#     if existing_pending:
#         raise HTTPException(
#             status_code=400,
#             detail="You already have a pending withdrawal. Please wait until it is processed."
#         )

#     # Check if user already withdrew today (Kenya time)
#     today_start = datetime(now.year, now.month, now.day, 0, 0, 0, tzinfo=KENYA_TZ)
#     today_end = datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=KENYA_TZ)
#     withdrawal_today = await db.execute(
#         select(Withdrawal).filter(
#             Withdrawal.user_id == current_user.id,
#             Withdrawal.created_at >= today_start,
#             Withdrawal.created_at <= today_end,
#             Withdrawal.status == "approved"
#         )
#     )
#     if withdrawal_today.scalar_one_or_none():
#         raise HTTPException(
#             status_code=400,
#             detail="You can only withdraw once per day."
#         )

#     # Wallet check
#     wallet_result = await db.execute(
#         select(Wallet).filter(Wallet.user_id == current_user.id)
#     )
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="Wallet not found")

#     if wallet.income < withdrawal.amount:
#         raise HTTPException(status_code=400, detail="Insufficient income balance")

#     # Tax calculation
#     tax = round(withdrawal.amount * TAX_RATE, 2)
#     net_amount = withdrawal.amount - tax

#     # Deduct full amount
#     wallet.income -= withdrawal.amount
#     db.add(wallet)

#     new_withdrawal = Withdrawal(
#         user_id=current_user.id,
#         name=withdrawal.name,
#         number=withdrawal.number,
#         amount=withdrawal.amount,
#         tax=tax,
#         net_amount=net_amount,
#         status="pending",
#         created_at=datetime.now(KENYA_TZ),
#     )
#     db.add(new_withdrawal)

#     # Ledger: withdrawal request
#     db.add(
#         Transaction(
#             user_id=current_user.id,
#             type="withdrawal_request",
#             amount=withdrawal.amount,
#             created_at=datetime.now(KENYA_TZ),
#         )
#     )

#     # Ledger: tax
#     db.add(
#         Transaction(
#             user_id=current_user.id,
#             type="withdrawal_tax",
#             amount=tax,
#             created_at=datetime.now(KENYA_TZ),
#         )
#     )

#     await db.commit()
#     await db.refresh(new_withdrawal)
#     return new_withdrawal




# # -------------------------
# # ADMIN: Get all withdrawals
# # -------------------------
# @router.get("/", response_model=List[WithdrawalResponse])
# async def get_all_withdrawals(
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(select(Withdrawal))
#     return result.scalars().all()

# # -------------------------
# # ADMIN: Approve / Reject
# # -------------------------
# @router.patch("/{withdrawal_id}/status", response_model=WithdrawalResponse)
# async def update_withdrawal_status(
#     withdrawal_id: int,
#     status_update: WithdrawalUpdateStatus,
#     admin: User = Depends(get_current_admin),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(Withdrawal).filter(Withdrawal.id == withdrawal_id)
#     )
#     withdrawal = result.scalar_one_or_none()

#     if not withdrawal:
#         raise HTTPException(status_code=404, detail="Withdrawal not found")

#     if withdrawal.status != "pending":
#         raise HTTPException(status_code=400, detail="Withdrawal already processed")

#     withdrawal.status = status_update.status.lower()
#     db.add(withdrawal)

#     wallet_result = await db.execute(
#         select(Wallet).filter(Wallet.user_id == withdrawal.user_id)
#     )
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="Wallet not found")

#     # REJECT → refund full amount
#     if withdrawal.status == "rejected":
#         wallet.income += withdrawal.amount
#         db.add(wallet)

#         db.add(
#             Transaction(
#                 user_id=withdrawal.user_id,
#                 type="withdrawal_rejected_refund",
#                 amount=withdrawal.amount,
#                 created_at=datetime.utcnow(),
#             )
#         )

#     # APPROVE → user receives net amount
#     if withdrawal.status == "approved":
#         db.add(
#             Transaction(
#                 user_id=withdrawal.user_id,
#                 type="withdrawal_approved",
#                 amount=withdrawal.net_amount,
#                 created_at=datetime.utcnow(),
#             )
#         )

#     await db.commit()
#     await db.refresh(withdrawal)
#     return withdrawal

# # -------------------------
# # USER: Get own withdrawals
# # -------------------------
# @router.get("/me", response_model=List[WithdrawalResponse])
# async def get_my_withdrawals(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(Withdrawal).filter(Withdrawal.user_id == current_user.id)
#     )
#     return result.scalars().all()




from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, time, timedelta, timezone

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
KENYA_TZ = timezone(timedelta(hours=3))  # UTC+3

def verify_pin(pin: str, hashed_pin: str) -> bool:
    return pwd_context_pin.verify(pin[:ARGON2_MAX_LENGTH], hashed_pin)

# -------------------------
# USER: Request withdrawal
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

    # Kenya time now
    now = datetime.now(KENYA_TZ)
    weekday = now.weekday()  # Monday=0, Sunday=6
    if weekday == 6:
        raise HTTPException(status_code=400, detail="Withdrawals not allowed on Sunday")

    if not (time(9, 0) <= now.time() <= time(18, 0)):
        raise HTTPException(status_code=400, detail="Withdrawals allowed only from 9AM to 6PM Kenya time")

    # Check existing pending withdrawals
    pending_result = await db.execute(
        select(Withdrawal).filter(
            Withdrawal.user_id == current_user.id,
            Withdrawal.status == "pending"
        )
    )
    existing_pending = pending_result.scalar_one_or_none()
    if existing_pending:
        raise HTTPException(
            status_code=400,
            detail="You already have a pending withdrawal. Please wait until it is processed."
        )

    # Check if user already withdrew today (Kenya time)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=None)
    withdrawal_today = await db.execute(
        select(Withdrawal).filter(
            Withdrawal.user_id == current_user.id,
            Withdrawal.created_at >= today_start,
            Withdrawal.created_at <= today_end,
            Withdrawal.status == "approved"
        )
    )
    if withdrawal_today.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="You can only withdraw once per day."
        )

    # Wallet check
    wallet_result = await db.execute(
        select(Wallet).filter(Wallet.user_id == current_user.id)
    )
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Wallet not found")

    if wallet.income < withdrawal.amount:
        raise HTTPException(status_code=400, detail="Insufficient income balance")

    # Tax calculation
    tax = round(withdrawal.amount * TAX_RATE, 2)
    net_amount = withdrawal.amount - tax

    # Deduct full amount
    wallet.income -= withdrawal.amount
    db.add(wallet)

    created_at = datetime.now(KENYA_TZ).replace(tzinfo=None)
    new_withdrawal = Withdrawal(
        user_id=current_user.id,
        name=withdrawal.name,
        number=withdrawal.number,
        amount=withdrawal.amount,
        tax=tax,
        net_amount=net_amount,
        status="pending",
        created_at=created_at,
    )
    db.add(new_withdrawal)

    # Ledger: withdrawal request
    db.add(
        Transaction(
            user_id=current_user.id,
            type="withdrawal_request",
            amount=withdrawal.amount,
            created_at=created_at,
        )
    )

    # Ledger: tax
    db.add(
        Transaction(
            user_id=current_user.id,
            type="withdrawal_tax",
            amount=tax,
            created_at=created_at,
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

    created_at = datetime.now(KENYA_TZ).replace(tzinfo=None)
    # REJECT → refund full amount
    if withdrawal.status == "rejected":
        wallet.income += withdrawal.amount
        db.add(wallet)

        db.add(
            Transaction(
                user_id=withdrawal.user_id,
                type="withdrawal_rejected_refund",
                amount=withdrawal.amount,
                created_at=created_at,
            )
        )

    # APPROVE → user receives net amount
    if withdrawal.status == "approved":
        db.add(
            Transaction(
                user_id=withdrawal.user_id,
                type="withdrawal_approved",
                amount=withdrawal.net_amount,
                created_at=created_at,
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
