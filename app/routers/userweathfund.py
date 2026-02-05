# # from fastapi import APIRouter, Depends, HTTPException
# # from sqlalchemy.ext.asyncio import AsyncSession
# # from sqlalchemy.future import select
# # from datetime import datetime, timedelta
# # from typing import List
# # from app.database.database import get_async_db
# # from app.models.models import WealthFund, UserWealthFund, Wallet, User
# # from app.routers.auth import get_current_user
# # from app.schema.schema import InvestWealthFundRequest, UserWealthFundResponse

# # router = APIRouter(prefix="/user-wealthfunds", tags=["User Wealth Funds"])

# # # -------------------------
# # # Update daily interest for active funds
# # # -------------------------
# # async def update_daily_interest(db: AsyncSession):
# #     now = datetime.utcnow()
# #     result = await db.execute(
# #         select(UserWealthFund)
# #         .filter(UserWealthFund.status == "active")
# #         .filter(UserWealthFund.end_date >= now)
# #     )
# #     active_funds = result.scalars().all()

# #     for fund in active_funds:
# #         # Today's interest = user's investment amount * daily_interest%
# #         today_interest = (fund.daily_interest / 100) * fund.amount
# #         fund.today_interest = today_interest
# #         # Total profit so far (without adding to wallet yet)
# #         fund.total_profit += today_interest

# #     await db.commit()

# # # -------------------------
# # # Complete matured wealth funds
# # # -------------------------
# # async def complete_matured_funds(db: AsyncSession):
# #     now = datetime.utcnow()
# #     result = await db.execute(
# #         select(UserWealthFund)
# #         .filter(UserWealthFund.status == "active")
# #         .filter(UserWealthFund.end_date <= now)
# #     )
# #     matured_funds = result.scalars().all()

# #     for fund in matured_funds:
# #         # Credit principal + total profit to wallet
# #         wallet_result = await db.execute(
# #             select(Wallet).filter(Wallet.user_id == fund.user_id)
# #         )
# #         wallet = wallet_result.scalar_one_or_none()
# #         if wallet:
# #             total_return = fund.amount + fund.total_profit
# #             wallet.income += total_return

# #         # Mark fund as completed
# #         fund.status = "completed"
# #         fund.today_interest = 0.0

# #     await db.commit()

# # # -------------------------
# # # USER: Invest in Wealth Fund
# # # -------------------------
# # @router.post("/invest", response_model=UserWealthFundResponse)
# # async def invest_in_wealthfund(
# #     data: InvestWealthFundRequest,
# #     user: User = Depends(get_current_user),
# #     db: AsyncSession = Depends(get_async_db),
# # ):
# #     # Get wealth fund
# #     result = await db.execute(
# #         select(WealthFund).filter(WealthFund.id == data.wealthfund_id)
# #     )
# #     wealthfund = result.scalar_one_or_none()

# #     if not wealthfund:
# #         raise HTTPException(status_code=404, detail="Wealth fund not found")

# #     # Get wallet
# #     wallet_result = await db.execute(
# #         select(Wallet).filter(Wallet.user_id == user.id)
# #     )
# #     wallet = wallet_result.scalar_one_or_none()

# #     if not wallet:
# #         raise HTTPException(status_code=400, detail="Wallet not found")

# #     # Check if user has enough balance for the investment amount they specified
# #     if wallet.income < data.amount:
# #         raise HTTPException(status_code=400, detail="Insufficient income balance")

# #     # Deduct user's investment amount from wallet income
# #     wallet.income -= data.amount

# #     start_date = datetime.utcnow()
# #     end_date = start_date + timedelta(days=wealthfund.duration_days)

# #     user_wealthfund = UserWealthFund(
# #         user_id=user.id,
# #         wealthfund_id=wealthfund.id,
# #         image=wealthfund.image,
# #         name=wealthfund.name,
# #         amount=data.amount,  # Use user's investment amount
# #         profit_percent=wealthfund.profit_percent,
# #         duration_days=wealthfund.duration_days,
# #         daily_interest=wealthfund.daily_interest,
# #         total_profit=0.0,
# #         today_interest=0.0,
# #         start_date=start_date,
# #         end_date=end_date,
# #         status="active",
# #     )

# #     db.add(user_wealthfund)
# #     db.add(wallet)
# #     await db.commit()
# #     await db.refresh(user_wealthfund)

# #     return user_wealthfund

# # # -------------------------
# # # USER: Get My Wealth Funds
# # # -------------------------
# # @router.get("/", response_model=List[UserWealthFundResponse])
# # async def get_my_wealthfunds(
# #     user: User = Depends(get_current_user),
# #     db: AsyncSession = Depends(get_async_db),
# # ):
# #     result = await db.execute(
# #         select(UserWealthFund)
# #         .filter(UserWealthFund.user_id == user.id)
# #         .order_by(UserWealthFund.created_at.desc())
# #     )
# #     return result.scalars().all()





# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from datetime import datetime, timedelta
# from typing import List
# from app.database.database import get_async_db
# from app.models.models import WealthFund, UserWealthFund, Wallet, User, Transaction
# from app.routers.auth import get_current_user
# from app.schema.schema import InvestWealthFundRequest, UserWealthFundResponse

# router = APIRouter(prefix="/user-wealthfunds", tags=["User Wealth Funds"])

# # -------------------------
# # Update daily interest for active funds
# # -------------------------
# async def update_daily_interest(db: AsyncSession):
#     now = datetime.utcnow()
#     result = await db.execute(
#         select(UserWealthFund)
#         .filter(UserWealthFund.status == "active")
#         .filter(UserWealthFund.end_date >= now)
#     )
#     active_funds = result.scalars().all()

#     for fund in active_funds:
#         # Today's interest = user's investment amount * daily_interest%
#         today_interest = (fund.daily_interest / 100) * fund.amount
#         fund.today_interest = today_interest
#         # Total profit so far (without adding to wallet yet)
#         fund.total_profit += today_interest

#     await db.commit()

# # -------------------------
# # Complete matured wealth funds
# # -------------------------
# async def complete_matured_funds(db: AsyncSession):
#     now = datetime.utcnow()
#     result = await db.execute(
#         select(UserWealthFund)
#         .filter(UserWealthFund.status == "active")
#         .filter(UserWealthFund.end_date <= now)
#     )
#     matured_funds = result.scalars().all()

#     for fund in matured_funds:
#         # Credit principal + total profit to wallet
#         wallet_result = await db.execute(
#             select(Wallet).filter(Wallet.user_id == fund.user_id)
#         )
#         wallet = wallet_result.scalar_one_or_none()
#         if wallet:
#             total_return = fund.amount + fund.total_profit
#             wallet.income += total_return

#             # Record transaction for maturity
#             db.add(Transaction(
#                 user_id=fund.user_id,
#                 type=f"wealth fund maturity: {fund.name}",
#                 amount=total_return,
#                 created_at=datetime.utcnow()
#             ))

#         # Mark fund as completed
#         fund.status = "completed"
#         fund.today_interest = 0.0

#     await db.commit()

# # -------------------------
# # USER: Invest in Wealth Fund
# # -------------------------
# @router.post("/invest", response_model=UserWealthFundResponse)
# async def invest_in_wealthfund(
#     data: InvestWealthFundRequest,
#     user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     # Get wealth fund
#     result = await db.execute(
#         select(WealthFund).filter(WealthFund.id == data.wealthfund_id)
#     )
#     wealthfund = result.scalar_one_or_none()

#     if not wealthfund:
#         raise HTTPException(status_code=404, detail="Wealth fund not found")

#     # Get wallet
#     wallet_result = await db.execute(
#         select(Wallet).filter(Wallet.user_id == user.id)
#     )
#     wallet = wallet_result.scalar_one_or_none()

#     if not wallet:
#         raise HTTPException(status_code=400, detail="Wallet not found")

#     # Check if user has enough balance for the investment amount they specified
#     if wallet.income < data.amount:
#         raise HTTPException(status_code=400, detail="Insufficient income balance")

#     # Deduct user's investment amount from wallet income
#     wallet.income -= data.amount

#     # Record transaction for investment
#     db.add(Transaction(
#         user_id=user.id,
#         type=f"wealth fund investment: {wealthfund.name}",
#         amount=data.amount,
#         created_at=datetime.utcnow()
#     ))

#     start_date = datetime.utcnow()
#     end_date = start_date + timedelta(days=wealthfund.duration_days)

#     user_wealthfund = UserWealthFund(
#         user_id=user.id,
#         wealthfund_id=wealthfund.id,
#         image=wealthfund.image,
#         name=wealthfund.name,
#         amount=data.amount,  # Use user's investment amount
#         profit_percent=wealthfund.profit_percent,
#         duration_days=wealthfund.duration_days,
#         daily_interest=wealthfund.daily_interest,
#         total_profit=0.0,
#         today_interest=0.0,
#         start_date=start_date,
#         end_date=end_date,
#         status="active",
#     )

#     db.add(user_wealthfund)
#     db.add(wallet)
#     await db.commit()
#     await db.refresh(user_wealthfund)

#     return user_wealthfund

# # -------------------------
# # USER: Get My Wealth Funds
# # -------------------------
# @router.get("/", response_model=List[UserWealthFundResponse])
# async def get_my_wealthfunds(
#     user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(
#         select(UserWealthFund)
#         .filter(UserWealthFund.user_id == user.id)
#         .order_by(UserWealthFund.created_at.desc())
#     )
#     return result.scalars().all()





from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta
from typing import List
from app.database.database import get_async_db
from app.models.models import WealthFund, UserWealthFund, Wallet, User, Transaction, TransactionType
from app.routers.auth import get_current_user
from app.schema.schema import InvestWealthFundRequest, UserWealthFundResponse

router = APIRouter(prefix="/user-wealthfunds", tags=["User Wealth Funds"])

# -------------------------
# Update daily interest for active funds
# -------------------------
async def update_daily_interest(db: AsyncSession):
    now = datetime.utcnow()
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.status == "active")
        .filter(UserWealthFund.end_date >= now)
    )
    active_funds = result.scalars().all()

    for fund in active_funds:
        today_interest = (fund.daily_interest / 100) * fund.amount
        fund.today_interest = today_interest
        fund.total_profit += today_interest

    await db.commit()

# -------------------------
# Complete matured wealth funds
# -------------------------
async def complete_matured_funds(db: AsyncSession):
    now = datetime.utcnow()
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.status == "active")
        .filter(UserWealthFund.end_date <= now)
    )
    matured_funds = result.scalars().all()

    for fund in matured_funds:
        wallet_result = await db.execute(
            select(Wallet).filter(Wallet.user_id == fund.user_id)
        )
        wallet = wallet_result.scalar_one_or_none()
        if wallet:
            total_return = fund.amount + fund.total_profit
            wallet.income += total_return

            # Record transaction using enum
            db.add(Transaction(
                user_id=fund.user_id,
                type=TransactionType.WEALTHFUND_MATURITY.value,
                amount=total_return,
                created_at=datetime.utcnow()
            ))

        fund.status = "completed"
        fund.today_interest = 0.0

    await db.commit()

# -------------------------
# USER: Invest in Wealth Fund
# -------------------------
@router.post("/invest", response_model=UserWealthFundResponse)
async def invest_in_wealthfund(
    data: InvestWealthFundRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(WealthFund).filter(WealthFund.id == data.wealthfund_id)
    )
    wealthfund = result.scalar_one_or_none()

    if not wealthfund:
        raise HTTPException(status_code=404, detail="Wealth fund not found")

    wallet_result = await db.execute(
        select(Wallet).filter(Wallet.user_id == user.id)
    )
    wallet = wallet_result.scalar_one_or_none()

    if not wallet:
        raise HTTPException(status_code=400, detail="Wallet not found")

    if wallet.income < data.amount:
        raise HTTPException(status_code=400, detail="Insufficient income balance")

    wallet.income -= data.amount

    # Record investment transaction
    db.add(Transaction(
        user_id=user.id,
        type=TransactionType.WEALTHFUND_INVESTMENT.value,
        amount=data.amount,
        created_at=datetime.utcnow()
    ))

    start_date = datetime.utcnow()
    end_date = start_date + timedelta(days=wealthfund.duration_days)

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
    db.add(wallet)
    await db.commit()
    await db.refresh(user_wealthfund)

    return user_wealthfund

# -------------------------
# USER: Get My Wealth Funds
# -------------------------
@router.get("/", response_model=List[UserWealthFundResponse])
async def get_my_wealthfunds(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(UserWealthFund)
        .filter(UserWealthFund.user_id == user.id)
        .order_by(UserWealthFund.created_at.desc())
    )
    return result.scalars().all()
