


from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Optional

from app.database.database import get_async_db
from app.models.models import Level, Task, User
from app.routers.auth import get_current_admin
from app.schema.schema import LevelCreate, LevelUpdate, LevelResponse

router = APIRouter(prefix="/levels", tags=["Levels"])


# -------------------------
# PUBLIC: Get all levels (with task count)
# -------------------------
@router.get("/", response_model=List[LevelResponse])
async def get_all_levels(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(
        select(
            Level,
            func.count(Task.id).label("task_count")
        )
        .outerjoin(Task, Task.level_id == Level.id)
        .group_by(Level.id)
    )

    levels = []
    for level, task_count in result.all():
        levels.append({
            "id": level.id,
            "name": level.name,
            "description": level.description,  # ✅ include description
            "earnest_money": level.earnest_money,
            "workload": level.workload,
            "salary": level.salary,
            "daily_income": level.daily_income,
            "monthly_income": level.monthly_income,
            "annual_income": level.annual_income,
            "task_count": task_count,
            "locked": bool(level.locked)
        })

    return levels


# -------------------------
# ADMIN: Create level
# -------------------------
@router.post("/", response_model=LevelResponse)
async def create_level(
    level: LevelCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    existing = await db.execute(select(Level).filter(Level.name == level.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Level already exists")

    new_level = Level(
        name=level.name,
        description=level.description,  # ✅ new field
        earnest_money=level.earnest_money,
        workload=level.workload,
        salary=level.salary,
        daily_income=level.daily_income,
        monthly_income=level.monthly_income,
        annual_income=level.annual_income,
        locked=level.locked if hasattr(level, "locked") else False
    )

    db.add(new_level)
    await db.commit()
    await db.refresh(new_level)

    return {
        "id": new_level.id,
        "name": new_level.name,
        "description": new_level.description,  # ✅ include description
        "earnest_money": new_level.earnest_money,
        "workload": new_level.workload,
        "salary": new_level.salary,
        "daily_income": new_level.daily_income,
        "monthly_income": new_level.monthly_income,
        "annual_income": new_level.annual_income,
        "task_count": 0,
        "locked": new_level.locked
    }


# -------------------------
# ADMIN: Update level (lock/unlock included)
# -------------------------
@router.patch("/{level_id}", response_model=LevelResponse)
async def update_level(
    level_id: int,
    level_update: LevelUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Level).filter(Level.id == level_id))
    level = result.scalar_one_or_none()

    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    for field, value in level_update.dict(exclude_unset=True).items():
        setattr(level, field, value)  # ✅ updates description if provided

    db.add(level)
    await db.commit()
    await db.refresh(level)

    task_count = await db.scalar(
        select(func.count(Task.id)).filter(Task.level_id == level.id)
    )

    return {
        "id": level.id,
        "name": level.name,
        "description": level.description,  # ✅ include description
        "earnest_money": level.earnest_money,
        "workload": level.workload,
        "salary": level.salary,
        "daily_income": level.daily_income,
        "monthly_income": level.monthly_income,
        "annual_income": level.annual_income,
        "task_count": task_count,
        "locked": level.locked
    }


# -------------------------
# ADMIN: Delete level
# -------------------------
@router.delete("/{level_id}")
async def delete_level(
    level_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Level).filter(Level.id == level_id))
    level = result.scalar_one_or_none()

    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    await db.delete(level)
    await db.commit()
    return {"message": "Level deleted successfully"}
