# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from typing import List
# from datetime import datetime

# from app.database.database import get_async_db
# from app.models.models import User, UserLevel, Level, Wallet, Task, UserTask, Transaction
# from app.routers.auth import get_current_user
# from app.schema.schema import BuyLevelRequest, UserLevelResponse, LevelInfoResponse

# router = APIRouter(prefix="/user-levels", tags=["User Levels"])


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
#     result = await db.execute(select(Level))
#     return result.scalars().all()


# # -------------------------
# # USER: Buy new level
# # -------------------------
# @router.post("/buy", response_model=UserLevelResponse)
# async def buy_level(
#     request: BuyLevelRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     # Fetch the level to buy
#     level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
#     level = level_result.scalar_one_or_none()
#     if not level:
#         raise HTTPException(status_code=404, detail="Level not found")

#     # Fetch user's wallet
#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     # Check if user already has a level
#     ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     if ul_result.scalar_one_or_none():
#         raise HTTPException(status_code=400, detail="You already own a level, use upgrade endpoint")

#     # Check balance
#     if wallet.balance < level.earnest_money:
#         raise HTTPException(status_code=400, detail="Insufficient balance to buy level")

#     # Deduct balance
#     wallet.balance -= level.earnest_money

#     # Record transaction
#     db.add(Transaction(
#         user_id=current_user.id,
#         type=f"buy {level.name}",
#         amount=level.earnest_money,
#         created_at=datetime.utcnow()
#     ))

#     # Create user level
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

#     # Assign tasks
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
#     return user_level


# # -------------------------
# # USER: Upgrade existing level
# # -------------------------
# @router.post("/upgrade", response_model=UserLevelResponse)
# async def upgrade_level(
#     request: BuyLevelRequest,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_async_db),
# ):
#     # Fetch the level to upgrade to
#     level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
#     level = level_result.scalar_one_or_none()
#     if not level:
#         raise HTTPException(status_code=404, detail="Level not found")

#     # Fetch user's wallet
#     wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
#     wallet = wallet_result.scalar_one_or_none()
#     if not wallet:
#         raise HTTPException(status_code=404, detail="User wallet not found")

#     # Fetch current level
#     ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
#     current_level = ul_result.scalar_one_or_none()
#     if not current_level:
#         raise HTTPException(status_code=400, detail="You don't have a level to upgrade, use buy endpoint")

#     if level.earnest_money <= current_level.earnest_money:
#         raise HTTPException(status_code=400, detail="You can only upgrade to a higher level")

#     difference = level.earnest_money - current_level.earnest_money
#     if wallet.balance < difference:
#         raise HTTPException(status_code=400, detail="Insufficient balance to upgrade")

#     # Deduct difference from balance and move old level to income
#     wallet.balance -= difference
#     wallet.income += current_level.earnest_money

#     # Record transaction
#     db.add(Transaction(
#         user_id=current_user.id,
#         type=f"upgrade {current_level.name} -> {level.name}",
#         amount=difference,
#         created_at=datetime.utcnow()
#     ))

#     # Remove old tasks
#     old_tasks_result = await db.execute(select(UserTask).filter(UserTask.user_id == current_user.id))
#     old_tasks = old_tasks_result.scalars().all()
#     for t in old_tasks:
#         await db.delete(t)

#     # Update UserLevel
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
#     return current_level






from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime

from app.database.database import get_async_db
from app.models.models import User, UserLevel, Level, Wallet, Task, UserTask, Transaction
from app.routers.auth import get_current_user
from app.schema.schema import BuyLevelRequest, UserLevelResponse, LevelInfoResponse

router = APIRouter(prefix="/user-levels", tags=["User Levels"])


# -------------------------
# USER: Get own levels
# -------------------------
@router.get("/me", response_model=List[UserLevelResponse])
async def get_my_levels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
    return result.scalars().all()


# -------------------------
# USER: Get all available levels (public)
# -------------------------
@router.get("/all", response_model=List[LevelInfoResponse])
async def get_all_levels(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(Level).filter(Level.locked == False))  # Only unlocked levels
    return result.scalars().all()


# -------------------------
# USER: Buy new level
# -------------------------
@router.post("/buy", response_model=UserLevelResponse)
async def buy_level(
    request: BuyLevelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Fetch the level to buy
    level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
    level = level_result.scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    # Check if level is locked
    if level.locked:
        raise HTTPException(status_code=403, detail="This level is currently locked")

    # Fetch user's wallet
    wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="User wallet not found")

    # Check if user already has a level
    ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
    if ul_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already own a level, use upgrade endpoint")

    # Check balance
    if wallet.balance < level.earnest_money:
        raise HTTPException(status_code=400, detail="Insufficient balance to buy level")

    # Deduct balance
    wallet.balance -= level.earnest_money

    # Record transaction
    db.add(Transaction(
        user_id=current_user.id,
        type=f"buy {level.name}",
        amount=level.earnest_money,
        created_at=datetime.utcnow()
    ))

    # Create user level
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
    tasks_result = await db.execute(select(Task).filter(Task.level_id == level.id))
    tasks = tasks_result.scalars().all()
    for t in tasks:
        db.add(UserTask(
            user_id=current_user.id,
            task_id=t.id,
            video_url=t.video_url,
            completed=False
        ))

    db.add(wallet)
    await db.commit()
    await db.refresh(user_level)
    return user_level


# -------------------------
# USER: Upgrade existing level
# -------------------------
@router.post("/upgrade", response_model=UserLevelResponse)
async def upgrade_level(
    request: BuyLevelRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Fetch the level to upgrade to
    level_result = await db.execute(select(Level).filter(Level.id == request.level_id))
    level = level_result.scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    # Check if level is locked
    if level.locked:
        raise HTTPException(status_code=403, detail="This level is currently locked")

    # Fetch user's wallet
    wallet_result = await db.execute(select(Wallet).filter(Wallet.user_id == current_user.id))
    wallet = wallet_result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="User wallet not found")

    # Fetch current level
    ul_result = await db.execute(select(UserLevel).filter(UserLevel.user_id == current_user.id))
    current_level = ul_result.scalar_one_or_none()
    if not current_level:
        raise HTTPException(status_code=400, detail="You don't have a level to upgrade, use buy endpoint")

    if level.earnest_money <= current_level.earnest_money:
        raise HTTPException(status_code=400, detail="You can only upgrade to a higher level")

    difference = level.earnest_money - current_level.earnest_money
    if wallet.balance < difference:
        raise HTTPException(status_code=400, detail="Insufficient balance to upgrade")

    # Deduct difference from balance and move old level to income
    wallet.balance -= difference
    wallet.income += current_level.earnest_money

    # Record transaction
    db.add(Transaction(
        user_id=current_user.id,
        type=f"upgrade {current_level.name} -> {level.name}",
        amount=difference,
        created_at=datetime.utcnow()
    ))

    # Remove old tasks
    old_tasks_result = await db.execute(select(UserTask).filter(UserTask.user_id == current_user.id))
    old_tasks = old_tasks_result.scalars().all()
    for t in old_tasks:
        await db.delete(t)

    # Update UserLevel
    current_level.level_id = level.id
    current_level.name = level.name
    current_level.description = level.description
    current_level.earnest_money = level.earnest_money
    current_level.workload = level.workload
    current_level.salary = level.salary
    current_level.daily_income = level.daily_income
    current_level.monthly_income = level.monthly_income
    current_level.annual_income = level.annual_income

    # Assign new tasks
    tasks_result = await db.execute(select(Task).filter(Task.level_id == level.id))
    tasks = tasks_result.scalars().all()
    for t in tasks:
        db.add(UserTask(
            user_id=current_user.id,
            task_id=t.id,
            video_url=t.video_url,
            completed=False
        ))

    db.add(wallet)
    await db.commit()
    await db.refresh(current_level)
    return current_level
