from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database.database import get_async_db
from app.models.models import WealthFund, User
from app.routers.auth import get_current_admin
from app.schema.schema import (
    WealthFundCreate,
    WealthFundUpdate,
    WealthFundResponse,
)

router = APIRouter(prefix="/wealthfunds", tags=["Wealth Funds"])


# -------------------------
# ADMIN: Get all wealth funds
# -------------------------
@router.get("/", response_model=List[WealthFundResponse])
async def get_all_wealthfunds(
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(WealthFund))
    return result.scalars().all()


# -------------------------
# ADMIN: Create wealth fund
# -------------------------
@router.post("/", response_model=WealthFundResponse)
async def create_wealthfund(
    data: WealthFundCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    existing = await db.execute(
        select(WealthFund).filter(WealthFund.name == data.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Wealth fund already exists")

    wealthfund = WealthFund(
        image=data.image,
        name=data.name,
        amount=data.amount,
        profit_percent=data.profit_percent,
        duration_days=data.duration_days,
        daily_interest=data.daily_interest,
    )

    db.add(wealthfund)
    await db.commit()
    await db.refresh(wealthfund)
    return wealthfund


# -------------------------
# ADMIN: Update wealth fund
# -------------------------
@router.patch("/{wealthfund_id}", response_model=WealthFundResponse)
async def update_wealthfund(
    wealthfund_id: int,
    data: WealthFundUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(WealthFund).filter(WealthFund.id == wealthfund_id)
    )
    wealthfund = result.scalar_one_or_none()

    if not wealthfund:
        raise HTTPException(status_code=404, detail="Wealth fund not found")

    for field, value in data.dict(exclude_unset=True).items():
        setattr(wealthfund, field, value)

    db.add(wealthfund)
    await db.commit()
    await db.refresh(wealthfund)
    return wealthfund


# -------------------------
# ADMIN: Delete wealth fund
# -------------------------
@router.delete("/{wealthfund_id}")
async def delete_wealthfund(
    wealthfund_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(WealthFund).filter(WealthFund.id == wealthfund_id)
    )
    wealthfund = result.scalar_one_or_none()

    if not wealthfund:
        raise HTTPException(status_code=404, detail="Wealth fund not found")

    await db.delete(wealthfund)
    await db.commit()
    return {"message": "Wealth fund deleted successfully"}
