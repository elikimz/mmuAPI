from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.database.database import get_async_db
from app.models.models import (
    Task,
    Level,
    User,
    UserLevel,
    UserTask,
    UserTaskPending,
    UserTaskCompleted,
)
from app.routers.auth import get_current_admin
from app.schema.schema import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# -------------------------
# PUBLIC: Get tasks by level
# -------------------------
@router.get("/level/{level_id}", response_model=List[TaskResponse])
async def get_tasks_by_level(
    level_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(Task).filter(Task.level_id == level_id)
    )
    return result.scalars().all()


# -------------------------
# ADMIN: Get all tasks
# -------------------------
@router.get("/", response_model=List[TaskResponse])
async def get_all_tasks(
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Task))
    return result.scalars().all()


# -------------------------
# ADMIN: Create task
# -------------------------
@router.post("/", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    # Ensure level exists
    level_result = await db.execute(
        select(Level).filter(Level.id == task.level_id)
    )
    level = level_result.scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found")

    # Create task
    new_task = Task(
        name=task.name,
        reward=task.reward,
        video_url=task.video_url,
        level_id=task.level_id,
    )
    db.add(new_task)
    await db.flush()  # 👈 allows access to new_task.id before commit

    # 🔥 Assign task to all users who already bought this level
    result = await db.execute(
        select(UserLevel).filter(UserLevel.level_id == task.level_id)
    )
    user_levels = result.scalars().all()

    for ul in user_levels:
        db.add(
            UserTask(
                user_id=ul.user_id,
                task_id=new_task.id,
                video_url=new_task.video_url,
                completed=False,
            )
        )

    await db.commit()
    await db.refresh(new_task)
    return new_task


# -------------------------
# ADMIN: Update task
# -------------------------
@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_level_id = task.level_id

    # If level is changed
    if task_update.level_id and task_update.level_id != old_level_id:
        level_result = await db.execute(
            select(Level).filter(Level.id == task_update.level_id)
        )
        if not level_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="New level not found")

        # Remove old user-task assignments
        await db.execute(
            UserTask.__table__.delete().where(UserTask.task_id == task.id)
        )

    for field, value in task_update.dict(exclude_unset=True).items():
        setattr(task, field, value)

    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# -------------------------
# ADMIN: Delete task
# -------------------------
@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(select(Task).filter(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Clean user-related task data
    await db.execute(
        UserTaskPending.__table__.delete().where(
            UserTaskPending.task_id == task_id
        )
    )
    await db.execute(
        UserTaskCompleted.__table__.delete().where(
            UserTaskCompleted.task_id == task_id
        )
    )
    await db.execute(
        UserTask.__table__.delete().where(UserTask.task_id == task_id)
    )

    await db.delete(task)
    await db.commit()
    return {"message": "Task deleted successfully"}
