




# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from typing import List
# from datetime import datetime

# from app.database.database import get_async_db
# from app.models.models import Referral, User, UserLevel, Level, Wallet, Task, UserTask, Transaction, TransactionType
# from app.routers.auth import get_current_user
# from app.schema.schema import BuyLevelRequest, UserLevelResponse, LevelInfoResponse
# from app.core.referalservices import process_referral_bonus

# router = APIRouter(prefix="/user-levels", tags=["User Levels"])


# # -------------------------
# # Helper to apply bonus to wallet and record transaction
# # -------------------------
# async def apply_referral_bonus(db: AsyncSession, user_id: int, bonus_amount: float, reason: str):
#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     # Add bonus to income
#     wallet.income += bonus_amount

#     # Record transaction using enum
#     db.add(Transaction(
#         user_id=user_id,
#         type=TransactionType.REFERRAL_BONUS.value,  # Updated here
#         amount=bonus_amount,
#         created_at=datetime.utcnow()
#     ))

#     db.add(wallet)
#     await db.commit()


# # -------------------------
# # USER: Get own levels
# # -------------------------
# @router.get("/me", response_model=List[UserLevelResponse])
# async def get_my_levels(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     return result.scalars().all()


# # -------------------------
# # USER: Get all available levels (public)
# # -------------------------
# @router.get("/all", response_model=List[LevelInfoResponse])
# async def get_all_levels(db: AsyncSession = Depends(get_async_db)):
#     result = await db.execute(select(Level).filter(Level.locked == False))  # Only unlocked levels
#     return result.scalars().all()




# # -------------------------
# # USER: Buy new level (fixed referral bonus)
# # -------------------------
# @router.post("/buy", response_model=UserLevelResponse)
# async def buy_level(
#     request: BuyLevelRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     # 1️⃣ Get the level
#     level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
#     level = level_result.scalar_one_or_none()
#     if not level:
#         raise HTTPException(status_code=404, detail="Level not found")
#     if level.locked:
#         raise HTTPException(status_code=403, detail="This level is currently locked")

#     # 2️⃣ Get wallet
#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     # 3️⃣ Check if user already has a level
#     ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     if ul_result.scalar_one_or_none():
#         raise HTTPException(status_code=400, detail="You already own a level, use upgrade endpoint")

#     if wallet.balance < level.earnest_money:
#         raise HTTPException(status_code=400, detail="Insufficient balance to buy level")

#     # 4️⃣ Deduct user's balance for level purchase
#     wallet.balance -= level.earnest_money
#     db.add(Transaction(
#         user_id=current_user.id,
#         type=TransactionType.LEVEL_PURCHASE.value,
#         amount=level.earnest_money,
#         created_at=datetime.utcnow()
#     ))

#     # 5️⃣ Create user level
#     user_level = UserLevel(
#         user_id=current_user.id,
#         level_id=level.id,
#         name=level.name,
#         description=level.description,
#         earnest_money=level.earnest_money,
#         workload=level.workload,
#         salary=level.salary,
#         daily_income=level.daily_income,
#         monthly_income=level.monthly_income,
#         annual_income=level.annual_income,
#     )
#     db.add(user_level)

#     # 6️⃣ Assign tasks
#     tasks_result = await db.execute(select(Task).filter(Task.level_id == level.id))
#     tasks = tasks_result.scalars().all()
#     for t in tasks:
#         db.add(UserTask(
#             user_id=current_user.id,
#             task_id=t.id,
#             video_url=t.video_url,
#             completed=False
#         ))

#     db.add(wallet)
#     await db.commit()
#     await db.refresh(user_level)

#     # 7️⃣ Apply referral bonus to referrer only
#     referrals_result = await db.execute(
#         select(Referral).where(Referral.referred_id == current_user.id)
#     )
#     referrals = referrals_result.scalars().all()

#     for ref in referrals:
#         # Skip if no active referrer level
#         referrer_level_result = await db.execute(
#             select(UserLevel).where(UserLevel.user_id == ref.referrer_id)
#         )
#         referrer_level = referrer_level_result.scalar_one_or_none()
#         if not referrer_level:
#             continue

#         bonus_base = min(referrer_level.salary, level.salary)
#         percent = {"A": 0.09, "B": 0.03, "C": 0.01}.get(ref.level, 0)
#         bonus_amount = round(bonus_base * percent, 2)
#         if bonus_amount <= 0:
#             continue

#         # Apply bonus to referrer's wallet
#         await apply_referral_bonus(
#             db=db,
#             user_id=ref.referrer_id,
#             bonus_amount=bonus_amount,
#             reason=f"Referral bonus from user {current_user.id} purchase"
#         )

#         # Mark referral as active
#         ref.is_active = True
#         ref.bonus_amount = bonus_amount
#         db.add(ref)

#     await db.commit()

#     return user_level


# # -------------------------
# # USER: Upgrade existing level (fixed referral bonus)
# # -------------------------
# @router.post("/upgrade", response_model=UserLevelResponse)
# async def upgrade_level(
#     request: BuyLevelRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
#     level = level_result.scalar_one_or_none()
#     if not level:
#         raise HTTPException(status_code=404, detail="Level not found")
#     if level.locked:
#         raise HTTPException(status_code=403, detail="This level is currently locked")

#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     current_level = ul_result.scalar_one_or_none()
#     if not current_level:
#         raise HTTPException(status_code=400, detail="You don't have a level to upgrade, use buy endpoint")
#     if level.earnest_money <= current_level.earnest_money:
#         raise HTTPException(status_code=400, detail="You can only upgrade to a higher level")

#     difference = level.earnest_money - current_level.earnest_money
#     if wallet.balance < difference:
#         raise HTTPException(status_code=400, detail="Insufficient balance to upgrade")

#     old_level_price = current_level.earnest_money

#     # Deduct difference
#     wallet.balance -= difference
#     wallet.income += old_level_price  # move old level price to income

#     db.add(Transaction(
#         user_id=current_user.id,
#         type=TransactionType.LEVEL_UPGRADE.value,
#         amount=difference,
#         created_at=datetime.utcnow()
#     ))

#     # Remove old tasks
#     old_tasks_result = await db.execute(select(UserTask).filter(UserTask.user_id == current_user.id))
#     old_tasks = old_tasks_result.scalars().all()
#     for t in old_tasks:
#         await db.delete(t)

#     # Update user level
#     current_level.level_id = level.id
#     current_level.name = level.name
#     current_level.description = level.description
#     current_level.earnest_money = level.earnest_money
#     current_level.workload = level.workload
#     current_level.salary = level.salary
#     current_level.daily_income = current_level.daily_income
#     current_level.monthly_income = current_level.monthly_income
#     current_level.annual_income = current_level.annual_income

#     # Assign new tasks
#     tasks_result = await db.execute(select(Task).filter(Task.level_id == level.id))
#     tasks = tasks_result.scalars().all()
#     for t in tasks:
#         db.add(UserTask(
#             user_id=current_user.id,
#             task_id=t.id,
#             video_url=t.video_url,
#             completed=False
#         ))

#     db.add(wallet)
#     await db.commit()
#     await db.refresh(current_level)

#     # Only apply referral bonus if upgrading from 0 level
#     if old_level_price == 0:
#         referrals_result = await db.execute(
#             select(Referral).where(Referral.referred_id == current_user.id)
#         )
#         referrals = referrals_result.scalars().all()

#         for ref in referrals:
#             referrer_level_result = await db.execute(
#                 select(UserLevel).where(UserLevel.user_id == ref.referrer_id)
#             )
#             referrer_level = referrer_level_result.scalar_one_or_none()
#             if not referrer_level:
#                 continue

#             bonus_base = min(referrer_level.salary, level.salary)
#             percent = {"A": 0.09, "B": 0.03, "C": 0.01}.get(ref.level, 0)
#             bonus_amount = round(bonus_base * percent, 2)
#             if bonus_amount <= 0:
#                 continue

#             await apply_referral_bonus(
#                 db=db,
#                 user_id=ref.referrer_id,
#                 bonus_amount=bonus_amount,
#                 reason=f"Referral bonus from user {current_user.id} upgrade"
#             )

#             ref.is_active = True
#             ref.bonus_amount = bonus_amount
#             db.add(ref)

#         await db.commit()

#     return current_level






# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from typing import List
# from datetime import datetime

# from app.database.database import get_async_db
# from app.models.models import Referral, User, UserLevel, Level, Wallet, Task, UserTask, Transaction, TransactionType
# from app.routers.auth import get_current_user
# from app.schema.schema import BuyLevelRequest, UserLevelResponse, LevelInfoResponse
# from app.core.referalservices import process_referral_bonus

# router = APIRouter(prefix="/user-levels", tags=["User Levels"])

# # -------------------------
# # Helper to apply bonus to wallet and record transaction
# # -------------------------
# async def apply_referral_bonus(db: AsyncSession, user_id: int, bonus_amount: float, reason: str):
#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     # Add bonus to income
#     wallet.income += bonus_amount

#     # Record transaction using enum
#     db.add(Transaction(
#         user_id=user_id,
#         type=TransactionType.REFERRAL_BONUS.value,
#         amount=bonus_amount,
#         created_at=datetime.utcnow()
#     ))

#     db.add(wallet)
#     await db.commit()

# # -------------------------
# # USER: Get own levels
# # -------------------------
# @router.get("/me", response_model=List[UserLevelResponse])
# async def get_my_levels(
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     return result.scalars().all()

# # -------------------------
# # USER: Get all available levels (public)
# # -------------------------
# @router.get("/all", response_model=List[LevelInfoResponse])
# async def get_all_levels(db: AsyncSession = Depends(get_async_db)):
#     result = await db.execute(select(Level).filter(Level.locked == False))  # Only unlocked levels
#     return result.scalars().all()

# # -------------------------
# # USER: Buy new level (fixed referral bonus)
# # -------------------------
# @router.post("/buy", response_model=UserLevelResponse)
# async def buy_level(
#     request: BuyLevelRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     # 1️⃣ Get the level
#     level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
#     level = level_result.scalar_one_or_none()
#     if not level:
#         raise HTTPException(status_code=404, detail="Level not found")
#     if level.locked:
#         raise HTTPException(status_code=403, detail="This level is currently locked")

#     # 2️⃣ Get wallet
#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     # 3️⃣ Check if user already has a level
#     ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     if ul_result.scalar_one_or_none():
#         raise HTTPException(status_code=400, detail="You already own a level, use upgrade endpoint")

#     if wallet.balance < level.earnest_money:
#         raise HTTPException(status_code=400, detail="Insufficient balance to buy level")

#     # 4️⃣ Deduct user's balance for level purchase
#     wallet.balance -= level.earnest_money
#     db.add(Transaction(
#         user_id=current_user.id,
#         type=TransactionType.LEVEL_PURCHASE.value,
#         amount=level.earnest_money,
#         created_at=datetime.utcnow()
#     ))

#     # 5️⃣ Create user level
#     user_level = UserLevel(
#         user_id=current_user.id,
#         level_id=level.id,
#         name=level.name,
#         description=level.description,
#         earnest_money=level.earnest_money,
#         workload=level.workload,
#         salary=level.salary,
#         daily_income=level.daily_income,
#         monthly_income=level.monthly_income,
#         annual_income=level.annual_income,
#     )
#     db.add(user_level)

#     # 6️⃣ Assign tasks
#     tasks_result = await db.execute(select(Task).filter(Task.level_id == level.id))
#     tasks = tasks_result.scalars().all()
#     for t in tasks:
#         db.add(UserTask(
#             user_id=current_user.id,
#             task_id=t.id,
#             video_url=t.video_url,
#             completed=False
#         ))

#     db.add(wallet)
#     await db.commit()
#     await db.refresh(user_level)

#     # 7️⃣ Apply referral bonus to referrer only
#     if level.salary > 0:  # Only apply bonus if the purchased level is not 0
#         referrals_result = await db.execute(
#             select(Referral).where(Referral.referred_id == current_user.id)
#         )
#         referrals = referrals_result.scalars().all()

#         for ref in referrals:
#             # Skip if no active referrer level
#             referrer_level_result = await db.execute(
#                 select(UserLevel).where(UserLevel.user_id == ref.referrer_id)
#             )
#             referrer_level = referrer_level_result.scalar_one_or_none()
#             if not referrer_level:
#                 continue

#             bonus_base = min(referrer_level.salary, level.salary)
#             percent = {"A": 0.09, "B": 0.03, "C": 0.01}.get(ref.level, 0)
#             bonus_amount = round(bonus_base * percent, 2)
#             if bonus_amount <= 0:
#                 continue

#             # Apply bonus to referrer's wallet
#             await apply_referral_bonus(
#                 db=db,
#                 user_id=ref.referrer_id,
#                 bonus_amount=bonus_amount,
#                 reason=f"Referral bonus from user {current_user.id} purchase"
#             )

#             # Mark referral as active
#             ref.is_active = True
#             ref.bonus_amount = bonus_amount
#             db.add(ref)

#     await db.commit()

#     return user_level

# # -------------------------
# # USER: Upgrade existing level (fixed referral bonus)
# # -------------------------
# @router.post("/upgrade", response_model=UserLevelResponse)
# async def upgrade_level(
#     request: BuyLevelRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
#     level = level_result.scalar_one_or_none()
#     if not level:
#         raise HTTPException(status_code=404, detail="Level not found")
#     if level.locked:
#         raise HTTPException(status_code=403, detail="This level is currently locked")

#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     current_level = ul_result.scalar_one_or_none()
#     if not current_level:
#         raise HTTPException(status_code=400, detail="You don't have a level to upgrade, use buy endpoint")
#     if level.earnest_money <= current_level.earnest_money:
#         raise HTTPException(status_code=400, detail="You can only upgrade to a higher level")

#     difference = level.earnest_money - current_level.earnest_money
#     if wallet.balance < difference:
#         raise HTTPException(status_code=400, detail="Insufficient balance to upgrade")

#     old_level_price = current_level.earnest_money

#     # Deduct difference
#     wallet.balance -= difference
#     wallet.income += old_level_price  # move old level price to income

#     db.add(Transaction(
#         user_id=current_user.id,
#         type=TransactionType.LEVEL_UPGRADE.value,
#         amount=difference,
#         created_at=datetime.utcnow()
#     ))

#     # Remove old tasks
#     old_tasks_result = await db.execute(select(UserTask).filter(UserTask.user_id == current_user.id))
#     old_tasks = old_tasks_result.scalars().all()
#     for t in old_tasks:
#         await db.delete(t)

#     # Update user level
#     current_level.level_id = level.id
#     current_level.name = level.name
#     current_level.description = level.description
#     current_level.earnest_money = level.earnest_money
#     current_level.workload = level.workload
#     current_level.salary = level.salary
#     current_level.daily_income = level.daily_income
#     current_level.monthly_income = level.monthly_income
#     current_level.annual_income = level.annual_income

#     # Assign new tasks
#     tasks_result = await db.execute(select(Task).filter(Task.level_id == level.id))
#     tasks = tasks_result.scalars().all()
#     for t in tasks:
#         db.add(UserTask(
#             user_id=current_user.id,
#             task_id=t.id,
#             video_url=t.video_url,
#             completed=False
#         ))

#     db.add(wallet)
#     await db.commit()
#     await db.refresh(current_level)

#     # Only apply referral bonus if upgrading from 0 level AND the new level is not 0
#     if old_level_price == 0 and level.salary > 0:
#         referrals_result = await db.execute(
#             select(Referral).where(Referral.referred_id == current_user.id)
#         )
#         referrals = referrals_result.scalars().all()

#         for ref in referrals:
#             referrer_level_result = await db.execute(
#                 select(UserLevel).where(UserLevel.user_id == ref.referrer_id)
#             )
#             referrer_level = referrer_level_result.scalar_one_or_none()
#             if not referrer_level:
#                 continue

#             bonus_base = min(referrer_level.salary, level.salary)
#             percent = {"A": 0.09, "B": 0.03, "C": 0.01}.get(ref.level, 0)
#             bonus_amount = round(bonus_base * percent, 2)
#             if bonus_amount <= 0:
#                 continue

#             await apply_referral_bonus(
#                 db=db,
#                 user_id=ref.referrer_id,
#                 bonus_amount=bonus_amount,
#                 reason=f"Referral bonus from user {current_user.id} upgrade"
#             )

#             ref.is_active = True
#             ref.bonus_amount = bonus_amount
#             db.add(ref)

#         await db.commit()

#     return current_level





from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime

from app.database.database import get_async_db
from app.models.models import Referral, User, UserLevel, Level, Wallet, Task, UserTask, Transaction, TransactionType
from app.routers.auth import get_current_user
from app.schema.schema import BuyLevelRequest, UserLevelResponse, LevelInfoResponse

router = APIRouter(prefix="/user-levels", tags=["User Levels"])

BONUS_PERCENTAGES = {"A": 0.09, "B": 0.03, "C": 0.01}

# -------------------------
# Helper to apply bonus to wallet and record transaction
# -------------------------
async def apply_referral_bonus(db: AsyncSession, user_id: int, bonus_amount: float):
    wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == user_id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="User wallet not found")

    wallet.income += bonus_amount

    db.add(Transaction(
        user_id=user_id,
        type=TransactionType.REFERRAL_BONUS.value,
        amount=bonus_amount,
        created_at=datetime.utcnow()
    ))

    db.add(wallet)
    await db.commit()


# -------------------------
# USER: Get own levels
# -------------------------
@router.get("/me", response_model=List[UserLevelResponse])
async def get_my_levels(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
    return result.scalars().all()


# -------------------------
# USER: Get all available levels
# -------------------------
@router.get("/all", response_model=List[LevelInfoResponse])
async def get_all_levels(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Level).filter(Level.locked == False))
    return result.scalars().all()


# ============================================================
# BUY LEVEL
# ============================================================
@router.post("/buy", response_model=UserLevelResponse)
async def buy_level(request: BuyLevelRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):

    level = (await db.execute(select(Level).filter(Level.id == request.level_id))).scalar_one_or_none()
    if not level:
        raise HTTPException(404, "Level not found")
    if level.locked:
        raise HTTPException(403, "This level is currently locked")

    wallet = (await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))).scalar_one_or_none()
    if not wallet:
        raise HTTPException(404, "User wallet not found")

    if (await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))).scalar_one_or_none():
        raise HTTPException(400, "You already own a level, use upgrade endpoint")

    if wallet.balance < level.earnest_money:
        raise HTTPException(400, "Insufficient balance to buy level")

    # Deduct purchase money
    wallet.balance -= level.earnest_money
    db.add(Transaction(user_id=current_user.id, type=TransactionType.LEVEL_PURCHASE.value, amount=level.earnest_money, created_at=datetime.utcnow()))

    # Create level
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
    )
    db.add(user_level)

    # Assign tasks
    tasks = (await db.execute(select(Task).filter(Task.level_id == level.id))).scalars().all()
    for t in tasks:
        db.add(UserTask(user_id=current_user.id, task_id=t.id, video_url=t.video_url, completed=False))

    db.add(wallet)
    await db.commit()
    await db.refresh(user_level)

    # =========================
    # REFERRAL BONUS (FIXED)
    # =========================
    if level.earnest_money > 0:   # 🚨 only paid levels generate bonus

        referrals = (await db.execute(select(Referral).where(Referral.referred_id == current_user.id))).scalars().all()

        for ref in referrals:
            referrer_level = (await db.execute(select(UserLevel).where(UserLevel.user_id == ref.referrer_id))).scalar_one_or_none()
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

    return user_level


# ============================================================
# UPGRADE LEVEL
# ============================================================
@router.post("/upgrade", response_model=UserLevelResponse)
async def upgrade_level(request: BuyLevelRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):

    level = (await db.execute(select(Level).filter(Level.id == request.level_id))).scalar_one_or_none()
    if not level:
        raise HTTPException(404, "Level not found")
    if level.locked:
        raise HTTPException(403, "This level is currently locked")

    wallet = (await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))).scalar_one_or_none()
    if not wallet:
        raise HTTPException(404, "User wallet not found")

    current_level = (await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))).scalar_one_or_none()
    if not current_level:
        raise HTTPException(400, "You don't have a level to upgrade")

    if level.earnest_money <= current_level.earnest_money:
        raise HTTPException(400, "Upgrade must be higher level")

    difference = level.earnest_money - current_level.earnest_money
    if wallet.balance < difference:
        raise HTTPException(400, "Insufficient balance")

    old_level_price = current_level.earnest_money

    wallet.balance -= difference
    wallet.income += old_level_price

    db.add(Transaction(user_id=current_user.id, type=TransactionType.LEVEL_UPGRADE.value, amount=difference, created_at=datetime.utcnow()))

    # Update level
    current_level.level_id = level.id
    current_level.name = level.name
    current_level.description = level.description
    current_level.earnest_money = level.earnest_money
    current_level.workload = level.workload
    current_level.salary = level.salary
    current_level.daily_income = level.daily_income
    current_level.monthly_income = level.monthly_income
    current_level.annual_income = level.annual_income

    db.add(wallet)
    await db.commit()
    await db.refresh(current_level)

    # =========================
    # REFERRAL BONUS ON FIRST PAID UPGRADE
    # =========================
    if old_level_price == 0 and level.earnest_money > 0:

        referrals = (await db.execute(select(Referral).where(Referral.referred_id == current_user.id))).scalars().all()

        for ref in referrals:
            referrer_level = (await db.execute(select(UserLevel).where(UserLevel.user_id == ref.referrer_id))).scalar_one_or_none()
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

    return current_level
