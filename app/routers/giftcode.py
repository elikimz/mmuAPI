from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from typing import List

from app.database.database import get_async_db
from app.models.models import GiftCode, GiftCodeRedemption, User
from app.routers.auth import get_current_admin, get_current_user
from app.schema.schema import GiftCodeCreate, GiftCodeRead, GiftCodeRedeem

router = APIRouter(prefix="/gift-codes", tags=["Gift Codes"])

# =====================================================
# Get All Gift Codes (Admin)
# =====================================================
@router.get("/", response_model=List[GiftCodeRead])
async def get_all_gift_codes(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(GiftCode).order_by(GiftCode.created_at.desc()))
    codes = result.scalars().all()

    if not codes:
        raise HTTPException(status_code=404, detail="No gift codes found")

    return codes


# =====================================================
# Create Gift Code (Admin)
# =====================================================
@router.post("/", response_model=GiftCodeRead, status_code=status.HTTP_201_CREATED)
async def create_gift_code(
    code: GiftCodeCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    db_code = GiftCode(
        code=code.code.upper(),
        amount=code.amount,
        is_active=code.is_active,
        max_uses=code.max_uses
    )

    db.add(db_code)

    try:
        await db.commit()
        await db.refresh(db_code)
        return db_code
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Gift code already exists")


# =====================================================
# Update Gift Code (Admin)
# =====================================================
@router.put("/{code_id}", response_model=GiftCodeRead)
async def update_gift_code(
    code_id: int,
    code: GiftCodeCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(GiftCode).where(GiftCode.id == code_id))
    db_code = result.scalar_one_or_none()

    if not db_code:
        raise HTTPException(status_code=404, detail="Gift code not found")

    db_code.code = code.code.upper()
    db_code.amount = code.amount
    db_code.is_active = code.is_active
    db_code.max_uses = code.max_uses

    try:
        await db.commit()
        await db.refresh(db_code)
        return db_code
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Another gift code with this name already exists")


# =====================================================
# Delete Gift Code (Admin)
# =====================================================
@router.delete("/{code_id}")
async def delete_gift_code(
    code_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(GiftCode).where(GiftCode.id == code_id))
    db_code = result.scalar_one_or_none()

    if not db_code:
        raise HTTPException(status_code=404, detail="Gift code not found")

    await db.delete(db_code)

    try:
        await db.commit()
        return {"message": "Gift code deleted successfully"}
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete gift code")


# =====================================================
# Redeem Gift Code (User)
# =====================================================
@router.post("/redeem/", response_model=GiftCodeRead)
async def redeem_gift_code(
    payload: GiftCodeRedeem,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    # 1️⃣ Find active gift code
    result = await db.execute(
        select(GiftCode).where(
            GiftCode.code == payload.code.upper(),
            GiftCode.is_active == True
        )
    )
    db_code = result.scalar_one_or_none()

    if not db_code:
        raise HTTPException(status_code=404, detail="Invalid or inactive gift code")

    # 2️⃣ Check global usage limit
    result = await db.execute(
        select(GiftCodeRedemption).where(GiftCodeRedemption.gift_code_id == db_code.id)
    )
    redeemed_count = len(result.scalars().all())

    if redeemed_count >= db_code.max_uses:
        raise HTTPException(status_code=400, detail="Gift code usage limit reached")

    # 3️⃣ Load wallet safely
    wallet_result = await db.execute(
        select(User)
        .where(User.id == user.id)
        .options(selectinload(User.wallet))
    )
    user_with_wallet = wallet_result.scalar_one()

    # 4️⃣ Credit wallet
    user_with_wallet.wallet.balance += db_code.amount

    # 5️⃣ Save redemption (UniqueConstraint handles duplicates)
    redemption = GiftCodeRedemption(
        user_id=user.id,
        gift_code_id=db_code.id,
        amount_claimed=db_code.amount
    )
    db.add(redemption)

    try:
        await db.commit()
        return db_code

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="You already redeemed this code")

    except Exception:
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to redeem gift code")
