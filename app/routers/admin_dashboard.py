from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Dict

from app.database.database import get_async_db
from app.models.models import User, Deposit, Withdrawal, UserWealthFund, Transaction
from app.routers.auth import get_current_admin

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard"])

@router.get("/stats")
async def get_admin_stats(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    # 1. Active Users (non-suspended)
    active_users_count = await db.scalar(
        select(func.count(User.id)).where(User.is_suspended == False)
    )

    # 2. Pending Requests (Pending Deposits + Pending Withdrawals)
    pending_deposits = await db.scalar(
        select(func.count(Deposit.id)).where(Deposit.status == "pending")
    )
    pending_withdrawals = await db.scalar(
        select(func.count(Withdrawal.id)).where(Withdrawal.status == "pending")
    )
    pending_requests_count = (pending_deposits or 0) + (pending_withdrawals or 0)

    # 3. Total Deposits (Sum of approved deposits)
    total_deposits_sum = await db.scalar(
        select(func.coalesce(func.sum(Deposit.amount), 0)).where(Deposit.status == "approved")
    )

    return {
        "active_users": active_users_count or 0,
        "pending_requests": pending_requests_count,
        "total_deposits": round(float(total_deposits_sum), 2),
    }

@router.get("/reports")
async def get_admin_reports(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    # Total Users
    total_users = await db.scalar(select(func.count(User.id)))
    
    # Total Investments
    total_investments = await db.scalar(
        select(func.coalesce(func.sum(UserWealthFund.amount), 0))
    )
    
    # Total Withdrawals (Approved)
    total_withdrawals = await db.scalar(
        select(func.coalesce(func.sum(Withdrawal.amount), 0)).where(Withdrawal.status == "approved")
    )
    
    # System Balance (Total Deposits - Total Withdrawals)
    total_deposits = await db.scalar(
        select(func.coalesce(func.sum(Deposit.amount), 0)).where(Deposit.status == "approved")
    )
    system_balance = float(total_deposits) - float(total_withdrawals)

    return {
        "total_users": total_users or 0,
        "total_investments": round(float(total_investments), 2),
        "total_withdrawals": round(float(total_withdrawals), 2),
        "system_balance": round(system_balance, 2),
        "total_deposits": round(float(total_deposits), 2),
    }
