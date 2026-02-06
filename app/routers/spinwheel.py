from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from datetime import datetime
from typing import List
import random

from app.database.database import get_async_db
from app.models.models import User, SpinWheelReward, UserSpin, SpinWheelConfig
from app.routers.auth import get_current_user
from app.schema.schema import (
    SpinWheelConfigBase, SpinWheelRewardCreate, SpinWheelRewardRead,
    UserSpinRead, SpinWheelRewardRead
)

router = APIRouter(prefix="/spin", tags=["Spin Wheel"])


# --------------------------
# Admin: Add Reward
# --------------------------
@router.post("/admin/reward", response_model=SpinWheelRewardRead)
async def add_reward(
    reward: SpinWheelRewardCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    new_reward = SpinWheelReward(**reward.dict())
    db.add(new_reward)
    await db.commit()
    await db.refresh(new_reward)
    return new_reward


# --------------------------
# Admin: Update Config
# --------------------------
@router.post("/admin/config", response_model=SpinWheelConfigBase)
async def update_config(
    config: SpinWheelConfigBase,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(select(SpinWheelConfig))
    wheel_config = result.scalar_one_or_none()

    if wheel_config:
        wheel_config.max_spins_per_day = config.max_spins_per_day
        wheel_config.is_active = config.is_active
    else:
        wheel_config = SpinWheelConfig(**config.dict())
        db.add(wheel_config)

    await db.commit()
    return config


# --------------------------
# User: Spin the Wheel
# --------------------------
@router.post("/user/spin", response_model=UserSpinRead)
async def spin_wheel(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Check if wheel is active
    result = await db.execute(select(SpinWheelConfig))
    wheel_config = result.scalar_one_or_none()
    if not wheel_config or not wheel_config.is_active:
        raise HTTPException(status_code=400, detail="Spin wheel is not active")

    # Check max spins per day
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    spins_today_query = await db.execute(
        select(func.count(UserSpin.id)).filter(
            UserSpin.user_id == current_user.id,
            UserSpin.created_at >= today_start
        )
    )
    spins_today = spins_today_query.scalar_one_or_none() or 0
    if spins_today >= wheel_config.max_spins_per_day:
        raise HTTPException(status_code=400, detail="Daily spin limit reached")

    # Fetch active rewards
    rewards_query = await db.execute(select(SpinWheelReward).filter(SpinWheelReward.is_active == True))
    rewards: List[SpinWheelReward] = rewards_query.scalars().all()
    if not rewards:
        raise HTTPException(status_code=400, detail="No rewards available")

    # Weighted random selection
    total_weight = sum(r.weight for r in rewards)
    r = random.uniform(0, total_weight)
    upto = 0
    selected_reward = rewards[-1]  # fallback
    for reward in rewards:
        if upto + reward.weight >= r:
            selected_reward = reward
            break
        upto += reward.weight

    # Save spin
    user_spin = UserSpin(user_id=current_user.id, reward_id=selected_reward.id)
    db.add(user_spin)
    await db.commit()
    await db.refresh(user_spin)

    # Return response manually with reward info
    return UserSpinRead(
        id=user_spin.id,
        created_at=user_spin.created_at,
        reward=SpinWheelRewardRead.from_orm(selected_reward)
    )


# --------------------------
# User: Spin History
# --------------------------
@router.get("/user/history", response_model=List[UserSpinRead])
async def get_spin_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(UserSpin).filter(UserSpin.user_id == current_user.id).order_by(UserSpin.created_at.desc())
    )
    spins: List[UserSpin] = result.scalars().all()

    # Manually attach reward info to avoid lazy-loading in async
    spins_read = []
    for spin in spins:
        reward_result = await db.execute(select(SpinWheelReward).filter(SpinWheelReward.id == spin.reward_id))
        reward = reward_result.scalar_one()
        spins_read.append(UserSpinRead(
            id=spin.id,
            created_at=spin.created_at,
            reward=SpinWheelRewardRead.from_orm(reward)
        ))
    return spins_read


# --------------------------
# User: Get active rewards
# --------------------------
@router.get("/user/rewards", response_model=List[SpinWheelRewardRead])
async def get_active_rewards(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(SpinWheelReward).filter(SpinWheelReward.is_active == True))
    rewards = result.scalars().all()
    return [SpinWheelRewardRead.from_orm(r) for r in rewards]
